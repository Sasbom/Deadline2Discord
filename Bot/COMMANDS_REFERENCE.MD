# Deadline2Discord Command Reference
_Written for Version 0.3, as of 3nd February 2024_

[Go back home, to README.md](../README.md)

The following docment describes all currently implemented functions of this bot, categorized.

The format is as follows: `/commandname subcommand (argument1) (argument2 [optional])`<br>
An optional argument is truly, optional.

### Basic commands

These are used to register yourself to the bot, allowing you access to it's functionality.

### /register
Register your username in the database, to allow jobs to be assigned to you and make yourself pingable.

### /deregister
Remove your username from the database. Makes you unpingable.

#### There's also some tools to calculate things, these will be expanded on in the future.

### /calculate rendertime (FPS) (Render Time) (Sequence duration) (PC Amount)
Small tool to calculate the total rendertime of an entire sequence, given:
- Frames per second
- Render time for each frame in either HH:MM:SS or MM:SS
- Sequence duration in either HH:MM:SS or MM:SS
- PC amount, basically the amount of nodes expected the job to be distributed over.

The arguments for this are listed as optional, they all have defaults, but its in your best interest to fill them all out.

---

### Job Control Commands

The meat and potatoes of this bot. All commands can be used to modify jobs that are registered. You can only do things with a job if you own it. You can make sure you own it or co own it, by making sure your **actual discord handle** is in the "Ping user(s)" box on the submitter, or is subscribed to a registered prism project. (The second name that appears below your display name when you view your profile on discord). 

View the main README.md to get a guide on how to modify your submission scripts to work with the bot.

### /job mine
Show all jobs that are registered to your name, with their status.

### /job stat (Job name)
Get a LOT of statistics about a job. It even includes a time estimate, that is calculated seperately from deadlines time estimator. This means that you can get an estimate faster!

### /job finish (Job name)
If a job is Completed/Failed, remove it from the database (will make your /job mine command faster.)

### /job finish_all
Finish off and remove all jobs from the database that have been completed or failed, and belong to you.

### /job fail (Job name)
Deliberately fail a job, if things are going wrong with it.

### /job suspend (Job name); /job resume (Job name)
Suspend (pause) or Resume (unpause) a job from running. This can be useful for getting out of people's hair when they are working, or when you are running a render that you are trying to fix by adjusting parameters.

### /job activehours set (Job name) (Time of suspension in HH:MM) (Time of resume in HH:MM)
Automagically make a job pause, and resume at the two given times.<br>
The time codes that work can be anywhere from `00:00` to `23:59`.

### /job activehours clear (Job name)
Don't schedule pausing/unpausing of specified job anymore, if it was set before with above command.

### /job requeue (Job name)
Requeue all tasks in a job, making it run all tasks again. Is exactly equivalent to requeueing in deadline monitor, and will change no parameters.

### /job reschedule (Job name) (Job new name) (New Scene file [optional]) (New Directory [optional]) (New Filename [optional]) (New Frames [optional]) (Submit Suspended [optional])

Now, This is quite the command. Luckily most of the arguments are optional.<br>
Reschedule a job as a new job with a new name, taking most of the same submission information with it and allowing for some change.

Arguments:
- Job Name: Old job's name to take info from
- Job new name: New name it will take on
- New Scene file: You can change the scene file it will render. This has to be compatible with the plugin that was previously used for the job, you can't reschedule a blender job as a maya job for example. This is very handy for times where you have a version b of a scene laying around that you also need to render. You can always copypaste a job scene file from /job stat.
- New Directory: Specify a new directory to render to.
- New Filename: Specify a new filename. Must include some #### for frame numbers, like `new_render_####.png`
- New Frames: Allows you to specify a new set of frames to render, following the deadline format, e.g. `0-10,200,390` to render frames zero through 10, frame 200 and frame 390. This can be very useful to isolate frames in a smaller job and do testing to fix errors, combined with the "New Scene file" argument.
- Submit suspended: If you don't want to immediatly run the job, submit it suspended and use the "/job activehours" functionality to schedule it for later.

**TODO: Add priority argument, as well as command for requesting available pools.**

---

### Prism Integration Commands

The basic workflow for using Prism pipeline with this is to install prism on a computer that is a node inside the deadline network, then make a project on some shared drive. The project's name is always included in the Deadline submission, so it's not possible to register your username to a project the normal way. This means that prism project pinging is subscription based. A project gets created, and if it has an unlocked state it allows for people to subscribe themselves to it, making them get a ping everytime an associated deadline job is finished. Prism projects in the bot have an owner that can manage their state. This feature already works, but might need some more administrative features exposed to users.

All subscribers and the owner become the owners of the render and can access it with the **/job** command set.

The bot's interactions with Prism are one sided and non-invasive to any Prism project itself.

### /prism list
Show all prism projects in the system, their subscribers, and locked/unlocked state.

### /prism register (Prism project name)
If you have a prism project created that publishes to the Deadline network, you can register it here. Make sure to match the spelling of the name exactly. Using this command will make you the owner of the project, and will allow you to lock/unlock it (discussed later). 

Registering a prism project does not subscribe you to it automatically. I have deliberately chosen for this behavior because someone else working in your group might want to manage/view the renders, while you maintain directive control.

### /prism deregister (Prism project name)
If you're the owner of a prism project, remove the prism project. This will automatically unsubscribe everyone and all results will not be caught by the bot anymore.

### /prism subscribe (Prism project name)
Subscribe to a prism project, if it's in an unlocked state. This will notify you when renders are complete. Requires you to be registered with **/register** so do that first.

### /prism unsubscribe (Prism project name)
Unsubscribe from a prism project.

### /prism lock (Prism project name)
If you are the owner of the project, lock the prism project. No one can subscribe to it anymore. Very useful if you don't want anyone to be nosy >:)

### /prism unlock (Prism project name)
If you are the owner of the project, unlock the prism project. People can subscribe to it again.

### /prism help (Nederlands [optional])
An overview of prism functionality like this documentation, also available in dutch if so desired.

---

### Global Farm Commands
#### Note: These require admin permission to use.

### Garbage Collection
Garbage collection generally refers to collecting any job that is present in the bot's database, but not in the actual deadline database. This can happen when a job is deleted in deadline monitor, for example. When polling for job status, it will report **Job is not present on server anymore**. The garbage collection procedure forces deadline monitor and the bot to be synced up again. 

It can be turned on to run periodically, but that feature is turned off by default because it can stall the bot for a long time.

### /farm garbagecollect set (Enabled) (Optional: Hour interval)

Turn automatic garbage collection, with an optional time interval in hours. The default is 24 hours, so every day since launch.

### /farm garbagecollect force

Force the garbage collection procedure to happen once.

---

### Suggestions?
Feel free to post them as issues or gists or what have you.
I hope this was useful.