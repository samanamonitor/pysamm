Scheduler will send attempts to the queue when are due. These attempts will live 60 seconds (by default) in the queue. If no collector picks them up, the attempt is lost. This is not a problem, as long as not many attempts are lost in the queue. To soften the peak of attempts that happens when the process is first started, the attempt is rescheduled when a done message is received from the collector. The new scheduled attempt should be:
(time in queue) + (process time) + (interval)
if the message is lost, the time is:
(interval)