RB
==

Renova Backup - a very lightweight and efficient tool for maintaining backup versions.
By Fabricio Kury -- fabriciokury@gmail.com -- github.com/fabkury

Coding start: Somewhere around april/2014.

Description:
A very small file move and versioning utility. The intended use case for this program is to continuously watch for and move incremental backups from an unprotected folder to a protected folder, and maintain versions of those files in that protected folder, replacing old ones with newer versions whenever necessary.
This program was designed to:
1) Be as efficient as possible by using the UNIX shell to move (rename) the files instead of copying them, and use rsync if moving was not possible. This means that the file operations inside one same filesystem will be very efficient.
2) Be as lightweight as possible, in order to run on restricted UNIX environments such as NAS CPUs, and in Python version 2.5.

Default configuration (backup versions):
* 1-14 days old
* 2-3 weeks old
* 1-5 months old
* older than 6 months

Command line usage:
-u: Process all folders now (kill -USR1)
-r: Create report now (kill -USR2)

TO DOs:
* Make a more configurable scheduling system.
* Read all configurations from a file. Separate the code from the local configurations.
* Make the code produce the S99rbd and Painel.php files.
* Make the system also move files lingering in the RB_SOURCE folder?
