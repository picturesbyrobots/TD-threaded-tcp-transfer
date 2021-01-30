# TD Threaded TCP Transfer

![Repo Logo](/src/img/repo-hero.png)

## what is this?
---
This is a pair of TOXs and associated scripts that allows the TD users to transfer an arbitrary number of files between networked computers running Touch Designer. Here's a GIF!


![GIF](/src/img/out.gif)

## What problem does this solve?
I wrote these modules because I found that I often had to solve the problem of getting files generated on one TD machine to another in a way that I could control without relying on buggy file shares or connecting to cloud internet servers. 

 ## Okie how does it work?
The modules use a TCP socket to transfer a Base64 encoded filestream. The payload is split into two parts. Part 1 is a small header of a fixed length that sends the server a filename and the length in bites of the incoming file. Part 2 is the actual file itself encoded in base64.


## Waiit. TD is Single Threaded. Won't my programs freeze while the file is transfering?
Yeah. That's way I've implemented both the client and server as seperate python threads. Unless something goes wrong you shouldn't notice any performance hits while they go about their work.


## Is this stable?
yes! I've been using this method on a number of production system without issue for the past few years with no complaints of crashes.

 **FULL DISCLOSURE**. Threading is tricky with TD. There might be some intermittent crashing during your setup process.  If you run anything open up an issue and I'll help sort it out!

## Ok how do I use it?
see the example send-a-file. You need to do three things.

1) Initialize the receiver TOX. This TOX should be placed in the machine you intend to receive files

2) Initialize the sender TOX. 

3) Call this line when you want to send a file : `op('img_sender').QueueJob(target_name=file_name, file_name=file_name)`

`QueueJob` takes two arguments: 
* `filename` This is the path to the file you intend to transfer.
* `target_name` This is the intended name of the transfered file

an example of setting up a job on a CHOP execute might look like this:
```
def onOffToOn(channel, sampleIndex, val, prev):
	file_path = op('get_file')['Banana.tif', 'path'].val
	file_name = 'Banana.tif'
	op('img_sender').QueueJob(target_name=file_name, file_name=file_path)
	return
```

*Special Note* There's also support for transfering multiple files:

```
def onOffToOn(channel, sampleIndex, val, prev):
	folder_dat = op('folder1')
	for row in folder_dat.rows()[1:] :
		target_name = row[0].val
		file_path = row[1].val
		op('img_sender').QueueJob(target_name=file_name,
									 file_name=file_path)

	return
```



## Development and Roadmap
If there's sufficient interest in the project I've got a couple of features that I think would be helpful. These include:
* A trigger that is fired on the receiver side whenever a transfer is complete
* some sort of indication or canary other than Text Port prints that would give the user an indication that the server is functional
* some sort of indication from the transfer process the indicates percentage of bytes transfered per job.
* a significant rewrite or example using the new fangled Engine TOX
* particles! 🎇🎇🎇🎇🎇🎇🎇




Have fun and stay safe out there.



