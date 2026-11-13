package lab;

import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import jdk.jfr.*;
import jdk.jfr.consumer.*;

/** Synthetic local work only. Every experiment asserts lifecycle/count invariants. */
public final class RuntimeLab {
    static final int SEED = 20261113;
    @Name("lab.TaskEvent") @Label("Lab task transition") @StackTrace(false)
    static class TaskEvent extends Event { String scenario; String transition; int task; }
    static Map<String,Object> obj(Object... kv) {
        Map<String,Object> m = new LinkedHashMap<>();
        for(int i=0;i<kv.length;i+=2) m.put((String)kv[i],kv[i+1]); return m;
    }
    static String json(Object x) {
        if(x==null) return "null";
        if(x instanceof String s) return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";
        if(x instanceof Number || x instanceof Boolean) return x.toString();
        if(x instanceof Map<?,?> m) return "{"+String.join(",",m.entrySet().stream().map(e->json(e.getKey().toString())+":"+json(e.getValue())).toList())+"}";
        if(x instanceof Collection<?> c) return "["+String.join(",",c.stream().map(RuntimeLab::json).toList())+"]";
        throw new IllegalArgumentException("Unsupported JSON value");
    }
    static void check(boolean b,String why) { if(!b) throw new IllegalStateException(why); }
    static double ms(long nanos) { return Math.round(nanos/1000.0)/1000.0; }
    static class Trace {
        final long origin=System.nanoTime(); final String scenario;
        final List<Map<String,Object>> events=new ArrayList<>();
        Trace(String s){scenario=s;}
        synchronized double emit(String state,int task, Object... extras) {
            double t=ms(System.nanoTime()-origin);
            Map<String,Object> e=obj("seq",events.size(),"ms",t,"state",state,"task",task);
            e.putAll(obj(extras)); events.add(e);
            TaskEvent j=new TaskEvent();j.scenario=scenario;j.transition=state;j.task=task;j.commit();return t;
        }
    }
    static ThreadPoolExecutor pool(int n,int q) {
        AtomicInteger ids=new AtomicInteger();
        return new ThreadPoolExecutor(n,n,0,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<>(q),r->{
            Thread t=new Thread(r,"lab-worker-"+ids.incrementAndGet()); t.setDaemon(true);return t;
        });
    }
    static void close(ThreadPoolExecutor p) throws Exception {
        p.shutdown();if(!p.awaitTermination(3,TimeUnit.SECONDS)){
            p.shutdownNow();check(p.awaitTermination(1,TimeUnit.SECONDS),"pool did not terminate");
            throw new IllegalStateException("pool exceeded graceful shutdown budget");
        }
    }
    static double percentile(List<Double> input,double p){
        List<Double>s=new ArrayList<>(input);Collections.sort(s);return s.get(Math.max(0,(int)Math.ceil(p*s.size())-1));
    }
    static Map<String,Object> saturation(String policy) throws Exception {
        Trace t=new Trace("pool_"+policy);ThreadPoolExecutor p=pool(2,3);
        AtomicInteger started=new AtomicInteger(),completed=new AtomicInteger(),rejected=new AtomicInteger(),overflow=new AtomicInteger(),caller=new AtomicInteger();
        CountDownLatch firstWorkers=new CountDownLatch(2);
        List<Double> latency=Collections.synchronizedList(new ArrayList<>());
        p.setRejectedExecutionHandler((r,e)->{
            overflow.incrementAndGet();
            if(policy.equals("abort")){rejected.incrementAndGet();t.emit("rejected",((Work)r).id,"queue",e.getQueue().size(),"active",e.getActiveCount());throw new RejectedExecutionException("synthetic saturation");}
            caller.incrementAndGet();t.emit("caller_runs",((Work)r).id,"queue",e.getQueue().size(),"active",e.getActiveCount());r.run();
        });
        try {
            for(int i=0;i<18;i++){
                int id=i;long submitted=System.nanoTime();
                t.emit("submitted",id,"queue",p.getQueue().size(),"active",p.getActiveCount());
                Work w=new Work(id,()->{
                    started.incrementAndGet();t.emit("started",id,"queue",p.getQueue().size(),"active",p.getActiveCount());
                    if(id<2)firstWorkers.countDown();
                    try{Thread.sleep(60);}catch(InterruptedException ex){Thread.currentThread().interrupt();throw new RuntimeException(ex);}
                    completed.incrementAndGet();latency.add(ms(System.nanoTime()-submitted));
                    t.emit("completed",id,"queue",p.getQueue().size(),"active",p.getActiveCount());
                });
                try{p.execute(w);}catch(RejectedExecutionException expected){}
                if(i==1)check(firstWorkers.await(1,TimeUnit.SECONDS),"workers never started");
                Thread.sleep(2);
            }
        }finally{close(p);}
        check(started.get()==completed.get(),"started != completed");
        check(18==completed.get()+rejected.get(),"offered != completed + rejected");
        check(overflow.get()>0,"did not saturate");
        check(!policy.equals("caller-runs")||caller.get()>0,"no caller feedback");
        return obj("policy",policy,"submitted",18,"started",started.get(),"completed",completed.get(),"rejected",rejected.get(),"overflow",overflow.get(),"callerRuns",caller.get(),"terminated",p.isTerminated(),"p50ms",percentile(latency,.5),"p95ms",percentile(latency,.95),"events",t.events);
    }
    record Work(int id,Runnable action) implements Runnable {public void run(){action.run();}}
    static Map<String,Object> cancellation(String mode) throws Exception {
        Trace t=new Trace("timeout_"+mode);ThreadPoolExecutor p=pool(1,1);
        CountDownLatch entered=new CountDownLatch(1),exited=new CountDownLatch(1);
        AtomicBoolean interrupted=new AtomicBoolean(),cancelResult=new AtomicBoolean();
        double[] exit={-1};String[] outcome={"completed"};
        Future<?> f=p.submit(()->{
            t.emit("started",0);long end=System.nanoTime()+TimeUnit.MILLISECONDS.toNanos(240);entered.countDown();
            try{
                while(System.nanoTime()<end){
                    try{TimeUnit.NANOSECONDS.sleep(Math.min(TimeUnit.MILLISECONDS.toNanos(10),Math.max(1,end-System.nanoTime())));}
                    catch(InterruptedException ex){interrupted.set(true);t.emit("interrupt_observed",0);
                        if(mode.equals("cooperative")){outcome[0]="interrupted";return;}
                        // Deliberate finite noncooperative control: continue only until the original 240 ms deadline.
                    }
                }
            }finally{exit[0]=t.emit("work_exited",0);exited.countDown();}
        });
        check(entered.await(1,TimeUnit.SECONDS),"worker did not enter");
        boolean timedOut=false;double returned=-1,signal=-1;
        try{f.get(40,TimeUnit.MILLISECONDS);}catch(TimeoutException expected){timedOut=true;returned=t.emit("waiter_returned",0);}
        if(!mode.equals("wait-only")){signal=t.emit("cancel_signal",0);cancelResult.set(f.cancel(true));t.emit("cancel_result",0,"accepted",cancelResult.get());}
        boolean exitedAtWaiterReturn=exited.getCount()==0;
        try{check(exited.await(2,TimeUnit.SECONDS),"work did not exit");}finally{close(p);}
        check(timedOut,"expected waiter timeout");check(!exitedAtWaiterReturn,"work already exited at timeout");
        check(exit[0]>=returned,"exit preceded timeout");
        if(mode.equals("wait-only"))check(!interrupted.get()&&!f.isCancelled(),"wait timeout cancelled work");
        else check(cancelResult.get()&&f.isCancelled()&&interrupted.get(),"cancel/interrupt not observed");
        if(mode.equals("ignore-interrupt"))check(exit[0]-returned>120,"noncooperative work stopped early");
        if(mode.equals("cooperative"))check(outcome[0].equals("interrupted"),"cooperative task did not exit on interrupt");
        return obj("mode",mode,"taskId",0,"waitTimeoutMs",40,"workBudgetMs",240,"waiterReturnedMs",returned,"cancelSignalMs",signal,"workExitedMs",exit[0],"workAfterWaiterMs",ms((long)((exit[0]-returned)*1e6)),"cancelAccepted",cancelResult.get(),"futureCancelled",f.isCancelled(),"interruptObserved",interrupted.get(),"outcome",outcome[0],"terminated",p.isTerminated(),"events",t.events);
    }
    static Map<String,Object> retries(String policy,int seed,int failures,int requests) throws Exception {
        Trace t=new Trace("retry_"+policy);Random random=new Random(seed);
        int attempts=0,success=0,failed=0;long sleepNanos=0;
        List<Integer> failureSchedule=new ArrayList<>();
        for(int id=0;id<requests;id++){
            // Fixed per-request failures: half intermittent, half persistent within the observed run.
            int fail=(id%2==0)?random.nextInt(3):failures;failureSchedule.add(fail);
            t.emit("request",id,"syntheticFailures",fail);
            int max=policy.equals("no-retry")?1:policy.equals("bounded-backoff")?3:Integer.MAX_VALUE;
            boolean ok=false;
            long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(2);
            for(int a=1;a<=max;a++){
                check(System.nanoTime()<deadline,"per-request safety watchdog (not a retry policy) reached");
                attempts++;t.emit("attempt",id,"attempt",a);
                Thread.sleep(2); // Local synthetic downstream service latency.
                if(a>fail){ok=true;t.emit("success",id,"attempt",a);break;}
                t.emit("attempt_failed",id,"attempt",a);
                if(policy.equals("bounded-backoff")&&a<max){
                    int planned=5*(1<<(a-1))+randomJitter(seed,id,a);
                    long before=System.nanoTime();Thread.sleep(planned);double actual=ms(System.nanoTime()-before);sleepNanos+=System.nanoTime()-before;
                    t.emit("backoff",id,"plannedMs",planned,"actualMs",actual);
                }
            }
            if(ok)success++;else{failed++;t.emit("request_failed",id);}
        }
        check(success+failed==requests,"request closure failed");
        if(policy.equals("bounded-backoff"))check(attempts<=3*requests,"bounded retry budget exceeded");
        if(policy.equals("unbounded-policy"))check(success==requests,"synthetic failures should recover");
        return obj("policy",policy,"requests",requests,"attempts",attempts,"success",success,"failed",failed,"amplification",Math.round(attempts*1000.0/requests)/1000.0,"backoffActualMs",ms(sleepNanos),"failureSchedule",failureSchedule,"events",t.events);
    }
    static int randomJitter(int seed,int id,int attempt){return new Random(seed+id*31L+attempt*7L).nextInt(4);}
    static Map<String,Object> jfrSummary(Path path) throws Exception {
        Map<String,Integer> counts=new TreeMap<>();
        Set<String> allowed=Set.of("lab.TaskEvent","jdk.ThreadSleep","jdk.ThreadPark","jdk.ExecutionSample");
        long total=0;Instant first=null,last=null;
        try(RecordingFile f=new RecordingFile(path)){
            while(f.hasMoreEvents()){
                RecordedEvent e=f.readEvent();total++;String name=e.getEventType().getName();
                if(allowed.contains(name))counts.merge(name,1,Integer::sum);
                if(first==null||e.getStartTime().isBefore(first))first=e.getStartTime();
                if(last==null||e.getEndTime().isAfter(last))last=e.getEndTime();
            }
        }
        check(counts.getOrDefault("lab.TaskEvent",0)>0,"JFR lacks actual lab events");
        check(counts.getOrDefault("jdk.ThreadSleep",0)>0,"JFR lacks actual sleep events");
        return obj("readable",true,"bytes",Files.size(path),"allEventsRead",total,"allowedEventCounts",counts,"observedSpanMs",Duration.between(first,last).toMillis(),"exportPolicy","counts-only; no threads, stack traces, paths, hosts or environment strings");
    }
    public static void main(String[] args) throws Exception {
        if(args.length==2&&args[0].equals("--read-jfr")){System.out.println(json(jfrSummary(Path.of(args[1]))));return;}
        Path out=Path.of("local/run.json"),jfr=Path.of("local/run.jfr");int seed=SEED,failures=6,requests=12;
        for(int i=0;i<args.length;i+=2){
            if(i+1>=args.length)throw new IllegalArgumentException("options require values");
            switch(args[i]){case "--out"->out=Path.of(args[i+1]);case "--jfr"->jfr=Path.of(args[i+1]);case "--seed"->seed=Integer.parseInt(args[i+1]);case "--failures"->failures=Integer.parseInt(args[i+1]);case "--requests"->requests=Integer.parseInt(args[i+1]);default->throw new IllegalArgumentException("unknown option");}
        }
        check(Runtime.version().toString().equals("25.0.5+8-LTS"),"Use Temurin 25.0.5+8 (LTS), pinned by the Lab");
        check(failures>=3&&failures<=20&&requests>=2&&requests<=40,"failures: 3..20, requests: 2..40");
        Files.createDirectories(out.toAbsolutePath().getParent());Files.createDirectories(jfr.toAbsolutePath().getParent());
        Map<String,Object> result=obj("schemaVersion",1,"recordType","measured-local-jvm","recordedAt",Instant.now().toString(),"seed",seed,"environment",obj("jdk",Runtime.version().toString(),"vendor",System.getProperty("java.vendor"),"os",System.getProperty("os.name"),"osVersion",System.getProperty("os.version"),"arch",System.getProperty("os.arch"),"logicalProcessors",Runtime.getRuntime().availableProcessors()),"config",obj("workers",2,"queueCapacity",3,"tasks",18,"arrivalDelayMs",2,"serviceMs",60,"waitTimeoutMs",40,"workBudgetMs",240,"requests",requests,"syntheticFailures",failures,"retryAttemptLimit",3,"downstreamMs",2));
        try(Recording recording=new Recording()){
            recording.enable(TaskEvent.class).withoutStackTrace();
            recording.enable("jdk.ThreadSleep").withThreshold(Duration.ZERO).withoutStackTrace();
            recording.enable("jdk.ThreadPark").withThreshold(Duration.ZERO).withoutStackTrace();
            recording.enable("jdk.ExecutionSample").withPeriod(Duration.ofMillis(20));recording.start();
            result.put("pools",List.of(saturation("abort"),saturation("caller-runs")));
            result.put("cancellation",List.of(cancellation("wait-only"),cancellation("ignore-interrupt"),cancellation("cooperative")));
            result.put("retries",List.of(retries("no-retry",seed,failures,requests),retries("unbounded-policy",seed,failures,requests),retries("bounded-backoff",seed,failures,requests)));
            recording.stop();recording.dump(jfr);
        }
        result.put("jfr",jfrSummary(jfr));result.put("assertionsPassed",true);
        Files.writeString(out,json(result)+"\n");System.out.println("PASS: lifecycle assertions, count closure, bounded retries, readable real JFR");
    }
}
