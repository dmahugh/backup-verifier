# backup-verifier
This is a tool to identify differences between one or more copies of a backup stream. I use this tool audit my backups occasionally, to verify that they're all 100% in synch with no missing files, extra files, or modified files.

![language:Python](https://img.shields.io/badge/Language-Python-blue.svg?style=flat-square) ![license:MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square) ![release:2.0](https://img.shields.io/badge/Release-1.0-lightgrey.svg?style=flat-square)

# Table of Contents
* [Background](#background)
* [Installation](#installation)
* [Usage](#usage)
* [Contributing](#contributing)
* [License](#license)

# Background
I blogged briefly about this tool [here](http://mahugh.com/2016/12/28/verifying-backup-drives/). It's something I've meant to write for years, because I don't care for the other ways to check differences between directory trees in Windows.

You can find details about my approach to managing my backups [here](http://mahugh.com/2013/04/02/my-backup-process/). I don't recommend my approach for others, because I don't care how you manage your backups and I certainly don't want any responsibility for how well your approach works. For me, though, this works great, and I have a backup stream that contains (among other things) every single photo I've ever taken that I felt was work keeping, including thousands of photos from pre-digital days and over 300,000 total photos now. If a cloud backup gives you what you want from life, you should stop reading and just do that instead. :)

# Installation
This program has no external dependencies, so if you have Python 3.5 or later installed you can just clone the repo and then run it with this command:

```python backup-verifier.py <masterdatafile> <backupcopy1> <backupcopy2> ...```

See below for more details on how to use it.

# Usage
/// basic concept
/// describe common use cases

![screenshot](///)

/// explain above example

# Contributing
This is a specialized little program that does exactly what I need, but if you'd like to submit a pull requests, note a bug, or comment on anything, feel free to [log an issue](https://github.com/dmahugh/backup-verifier/issues).

# License
This program is licensed under the [MIT License](https://github.com/dmahugh/backup-verifier/blob/master/LICENSE).

Copyright &copy; 2016 by Doug Mahugh
