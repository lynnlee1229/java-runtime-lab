package lab;

import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import jdk.jfr.*;
import jdk.jfr.consumer.*;
import static lab.RuntimeLab.*;

/** Original offline exercise: real virtual threads, an explicit downstream resource boundary. */
public final class BulkheadLab {
    static final List<String> JFR_EVENTS = List.of("lab.BulkheadEvent", "jdk.VirtualThreadStart",
        "jdk.VirtualThreadEnd", "jdk.VirtualThreadPinned", "jdk.VirtualThreadSubmitFailed", "jdk.ThreadPark", "jdk.ThreadSleep");

    @Name("lab.BulkheadEvent") @Label("Bulkhead transition") @StackTrace(false)
    static class Transition extends Event {
        String scenario, transition; int task, active, queued; boolean virtualThread;
    }

    // Updates and their trace snapshots share one short critical section. No blocking work holds it.
    static final class State {
        final String name; final int capacity; final long origin=System.nanoTime();
        final List<Map<String,Object>> events=new ArrayList<>();
        int active, queued, maxActive, maxQueued, entered, completed, rejected, cancelled, overCapacity, virtualTasks;
        State(String name,int capacity){this.name=name;this.capacity=capacity;}
        synchronized void emit(String event,int id,Object... extra) {
            switch(event) {
                case "started" -> {check(Thread.currentThread().isVirtual(),"task is not virtual");virtualTasks++;}
                case "queued" -> queued++;
                case "dequeued" -> queued--;
                case "entered" -> {active++;entered++;if(active>capacity)overCapacity++;}
                case "exited" -> active--;
                case "completed" -> completed++;
                case "rejected" -> rejected++;
                case "cancelled" -> cancelled++;
            }
            check(active>=0&&queued>=0,"negative resource accounting");
            maxActive=Math.max(maxActive,active);maxQueued=Math.max(maxQueued,queued);
            boolean virtual=Thread.currentThread().isVirtual();
            Map<String,Object> row=obj("seq",events.size(),"ms",ms(System.nanoTime()-origin),"state",event,
                "task",id,"active",active,"queued",queued,"virtualThread",virtual);
            row.putAll(obj(extra));events.add(row);
            Transition e=new Transition();e.scenario=name;e.transition=event;e.task=id;
            e.active=active;e.queued=queued;e.virtualThread=virtual;e.commit();
        }
        synchronized Map<String,Object> snapshot(){return obj("active",active,"queued",queued,"completed",completed,"rejected",rejected,"cancelled",cancelled);}
        Map<String,Object> result(int n,Semaphore slots,ExecutorService executor) {
            check(active==0&&queued==0&&completed+rejected+cancelled==n,"task closure failed");
            check(slots==null||slots.availablePermits()==capacity,"permit leak");
            check(executor.isTerminated(),"executor not terminated");
            return obj("policy",name,"submitted",n,"virtualTasks",virtualTasks,"capacity",capacity,
                "entered",entered,"completed",completed,"rejected",rejected,"cancelled",cancelled,
                "maxActive",maxActive,"maxQueued",maxQueued,"overCapacityEntries",overCapacity,
                "finalActive",active,"finalQueued",queued,"permitsRemaining",slots==null?null:slots.availablePermits(),
                "terminated",executor.isTerminated(),"events",events);
        }
    }
    static void await(CountDownLatch latch,String why) throws InterruptedException {
        check(latch.await(3,TimeUnit.SECONDS),"watchdog: "+why);
    }
    static void shutdown(ExecutorService executor) throws InterruptedException {
        executor.shutdown();
        if(!executor.awaitTermination(2,TimeUnit.SECONDS)) {
            executor.shutdownNow();check(executor.awaitTermination(1,TimeUnit.SECONDS),"executor cleanup failed");
            throw new IllegalStateException("executor exceeded shutdown deadline");
        }
    }
    static void join(List<Future<?>> futures) throws Exception {
        for(Future<?> f:futures)try{f.get(1,TimeUnit.SECONDS);}catch(CancellationException expected){}
    }

    static Map<String,Object> burst(String policy,int n,int capacity) throws Exception {
        State state=new State(policy,capacity);
        Semaphore slots=policy.equals("unbounded")?null:new Semaphore(capacity,true);
        ExecutorService executor=Executors.newVirtualThreadPerTaskExecutor();
        CountDownLatch reached=new CountDownLatch(n),release=new CountDownLatch(1),finished=new CountDownLatch(n);
        List<Future<?>> futures=new ArrayList<>();Map<String,Object> held;
        try {
            for(int i=0;i<n;i++) {
                int id=i;state.emit("submitted",id);
                futures.add(executor.submit(()->{
                    boolean permit=false,waiting=false,inside=false,arrived=false,ok=false;
                    state.emit("started",id);
                    try {
                        if(slots!=null) {
                            if(slots.tryAcquire())permit=true;
                            else if(policy.equals("reject")){state.emit("rejected",id);reached.countDown();arrived=true;return;}
                            else {
                                waiting=true;state.emit("queued",id);reached.countDown();arrived=true;
                                slots.acquire();permit=true;state.emit("dequeued",id);waiting=false;
                            }
                        }
                        state.emit("entered",id);inside=true;
                        if(!arrived){reached.countDown();arrived=true;}
                        await(release,"downstream release");Thread.sleep(10);ok=true;
                    } catch(InterruptedException e) {
                        state.emit("interrupt_observed",id);Thread.currentThread().interrupt();
                        throw new RuntimeException("unexpected burst interruption",e);
                    } finally {
                        if(waiting)state.emit("dequeued",id);
                        if(inside)state.emit("exited",id);
                        if(permit)slots.release();
                        if(ok)state.emit("completed",id);
                        if(!arrived)reached.countDown();finished.countDown();
                    }
                }));
            }
            await(reached,"all tasks reach the controlled first wave");
            held=state.snapshot();state.emit("held_snapshot",-1);
            check(state.active==(slots==null?n:capacity),"first wave active count");
            check(state.queued==(policy.equals("queue")?n-capacity:0),"first wave queue count");
            check(state.rejected==(policy.equals("reject")?n-capacity:0),"first wave rejection count");
            release.countDown();await(finished,"burst completion");join(futures);
        } finally {release.countDown();shutdown(executor);}
        Map<String,Object> result=state.result(n,slots,executor);result.put("heldSnapshot",held);return result;
    }

    static Map<String,Object> cancellation(boolean ignore,int capacity) throws Exception {
        String policy=ignore?"cancel-ignore":"cancel-cooperative";
        int n=capacity+1;State state=new State(policy,capacity);Semaphore slots=new Semaphore(capacity,true);
        ExecutorService executor=Executors.newVirtualThreadPerTaskExecutor();
        CountDownLatch holders=new CountDownLatch(capacity),queued=new CountDownLatch(1),release=new CountDownLatch(1);
        CountDownLatch finished=new CountDownLatch(n),interruptSeen=new CountDownLatch(1);
        CountDownLatch[] exited=new CountDownLatch[n];for(int i=0;i<n;i++)exited[i]=new CountDownLatch(1);
        List<Future<?>> futures=new ArrayList<>();Map<String,Object> atCancel;
        boolean waiterTimedOut=false,queuedAccepted=false,activeAccepted=false;
        try {
            for(int i=0;i<n;i++) {
                if(i==capacity)await(holders,"initial permit holders");
                int id=i;state.emit("submitted",id);
                futures.add(executor.submit(()->{
                    boolean permit=false,waiting=false,inside=false,interrupted=false;
                    state.emit("started",id);
                    try {
                        if(id==capacity){waiting=true;state.emit("queued",id);queued.countDown();}
                        slots.acquire();permit=true;
                        if(waiting){state.emit("dequeued",id);waiting=false;}
                        inside=true;state.emit("entered",id);holders.countDown();
                        try{await(release,"cancellation downstream release");}
                        catch(InterruptedException e) {
                            interrupted=true;state.emit("interrupt_observed",id);interruptSeen.countDown();
                            // Finite negative control. Future cancellation cannot free a resource still used by work.
                            if(ignore&&id==0)await(release,"finite ignore-interrupt control");
                        }
                    } catch(InterruptedException e) {
                        interrupted=true;state.emit("interrupt_observed",id);
                    } finally {
                        if(waiting)state.emit("dequeued",id);
                        if(inside)state.emit("exited",id);
                        if(permit)slots.release();
                        state.emit(interrupted?"cancelled":"completed",id);
                        exited[id].countDown();finished.countDown();
                    }
                }));
            }
            await(queued,"queued cancellation target");
            try{futures.get(0).get(35,TimeUnit.MILLISECONDS);}
            catch(TimeoutException expected){waiterTimedOut=true;state.emit("waiter_timeout",0);}
            check(waiterTimedOut,"holder must still own its permit at waiter timeout");
            state.emit("cancel_signal",capacity);queuedAccepted=futures.get(capacity).cancel(true);
            state.emit("cancel_result",capacity,"accepted",queuedAccepted);await(exited[capacity],"queued task exit");
            state.emit("cancel_signal",0);activeAccepted=futures.get(0).cancel(true);
            state.emit("cancel_result",0,"accepted",activeAccepted);await(interruptSeen,"holder sees interrupt");
            if(!ignore)await(exited[0],"cooperative holder exit");
            atCancel=state.snapshot();atCancel.put("targetWorkExited",exited[0].getCount()==0);
            atCancel.put("targetFutureCancelled",futures.get(0).isCancelled());
            state.emit("cancel_snapshot",-1);
            check(state.active==(ignore?capacity:capacity-1)&&state.queued==0,"cancellation resource state");
            check(queuedAccepted&&activeAccepted,"cancellation not accepted");
            release.countDown();await(finished,"all task finally blocks");join(futures);
        } finally {release.countDown();shutdown(executor);}
        Map<String,Object> result=state.result(n,slots,executor);
        result.put("waitBudgetMs",35);result.put("waiterTimedOut",waiterTimedOut);
        result.put("queuedCancelAccepted",queuedAccepted);result.put("activeCancelAccepted",activeAccepted);
        result.put("cancelSnapshot",atCancel);return result;
    }

    static Map<String,Object> readJfr(Path path) throws Exception {
        Map<String,Integer> counts=new TreeMap<>(),transitions=new TreeMap<>();
        for(String name:JFR_EVENTS)counts.put(name,0);
        try(RecordingFile file=new RecordingFile(path)) {
            while(file.hasMoreEvents()) {
                RecordedEvent e=file.readEvent();String name=e.getEventType().getName();
                if(counts.containsKey(name))counts.merge(name,1,Integer::sum);
                if(name.equals("lab.BulkheadEvent"))
                    transitions.merge(e.getString("scenario")+"/"+e.getString("transition"),1,Integer::sum);
            }
        }
        check(counts.get("lab.BulkheadEvent")>0&&counts.get("jdk.VirtualThreadStart")>0&&counts.get("jdk.VirtualThreadEnd")>0,"missing actual JFR evidence");
        return obj("readable",true,"bytes",Files.size(path),"enabledEvents",JFR_EVENTS,
            "eventCounts",counts,"transitionCounts",transitions,"exportPolicy","allowlisted counts only; raw JFR stays local",
            "absenceBoundary","zero pinned events means none recorded in this workload; it does not prove pinning is impossible");
    }
    public static void main(String[] args) throws Exception {
        if(args.length==2&&args[0].equals("--read-jfr")){System.out.println(json(readJfr(Path.of(args[1]))));return;}
        Path out=Path.of("local/bulkhead-1.json"),jfr=Path.of("local/bulkhead-1.jfr");int n=12,capacity=3;
        for(int i=0;i<args.length;i+=2) {
            if(i+1>=args.length)throw new IllegalArgumentException("options require values");
            switch(args[i]) {
                case "--out"->out=Path.of(args[i+1]);case "--jfr"->jfr=Path.of(args[i+1]);
                case "--requests"->n=Integer.parseInt(args[i+1]);case "--capacity"->capacity=Integer.parseInt(args[i+1]);
                default->throw new IllegalArgumentException("unknown option");
            }
        }
        check(Runtime.version().toString().equals("25.0.5+8-LTS"),"Use the existing pinned Temurin 25.0.5+8 LTS");
        check(capacity>=1&&capacity<=6&&n>capacity&&n<=40,"capacity: 1..6; requests: capacity+1..40");
        Files.createDirectories(out.toAbsolutePath().getParent());Files.createDirectories(jfr.toAbsolutePath().getParent());
        Map<String,Object> result=obj("schemaVersion",1,"recordType","measured-virtual-thread-bulkhead",
            "recordedAt",Instant.now().toString(),"runtime",Runtime.version().toString(),
            "config",obj("requests",n,"capacity",capacity,"serviceMs",10,"waitBudgetMs",35,"watchdogSeconds",3,
                "workload","local gated synthetic downstream; no network or model call"));
        try(Recording recording=new Recording()) {
            for(String name:JFR_EVENTS)recording.enable(name).withThreshold(Duration.ZERO).withoutStackTrace();
            recording.start();
            result.put("cases",List.of(burst("unbounded",n,capacity),burst("queue",n,capacity),burst("reject",n,capacity),
                cancellation(false,capacity),cancellation(true,capacity)));
            recording.stop();recording.dump(jfr);
        }
        result.put("jfr",readJfr(jfr));result.put("assertionsPassed",true);
        Files.writeString(out,json(result)+"\n");
        System.out.println("PASS: real virtual threads, controlled downstream capacity, queue/reject, cancellation and actual JFR");
    }
}
