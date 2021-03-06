
Luminotes
=========

This repo is an attempt to update the old luminotes wiki note suite for more recent versions of python, CherryPy, etc.



!!!WARNING!!!
=============

This code is in the process of being resurrected, so much of this information
is not accurate. Updates will occur Real Soon. Things to watch out for are
version incompatibilities, as this code is being updated for newer versions of
CherryPy.


Luminotes is a WYSIWYG personal wiki notebook for organizing your notes and
ideas. 

Windows Vista / 7
------------------

Note: These instructions have not been tested with the latest changes.

To start Luminotes Desktop on Windows, just click the Start button, click on
"All Programs", and then click on "Luminotes". Luminotes Desktop runs inside a
browser, so when you launch it, it will open up in a new browser window or
tab.

 * Windows Security: The first time you start Luminotes, you may see a Windows
Security Alert about blocking Luminotes. This is basically Windows asking you
if you want to allow Luminotes to access the internet. If you click "Keep
Blocking", then that will prevent Luminotes Desktop from accessing the
internet. If you click "Unblock", then Luminotes will be able to use your
internet connection.

Right now, Luminotes does not use the internet at all. However, a future
release will include the optional ability for you to synchronize your notes
with Luminotes.com. If you plan on using this synchronization feature when
it's available, then you should click "Unblock". Otherwise, you can safely
click "Keep Blocking".

 * File storage: In case you're curious, your notes are stored within
the %APPDATA%\Luminotes folder in a database file. Attached files are stored
within the %APPDATA\Luminotes\files folder. (It is not recommended that you
modify or copy these files.)

 * USB drive: If you'd like to run Luminotes from a USB drive, then when the
Luminotes Desktop installer prompts you to select the installation destination
location, simply select the location of your USB drive. For instance, if your
USB drive has the Windows drive letter "E:", then just enter "E:" for the
destination location.

(If you have already installed Luminotes Desktop, then you can just manually
copy the installed \Program Files\Luminotes folder to your USB drive.)

Once Luminotes Desktop is installed, instead of running Luminotes normally,
open your USB drive as a folder in Windows. Then, run usb_luminotes.bat from
the USB drive. Your Luminotes data, including all of your notes and notebooks,
will be stored on the USB drive instead of on the computer itself.

When you are done using Luminotes and you want to remove the USB drive, first
click the "close" link at the top of the page to completely shut down
Luminotes. Then, anytime you want to start Luminotes on the USB drive, run
usb_luminotes.bat from it.


Linux / Mac OS X / BSD
----------------------

To start Lumintoes Desktop or Server on Linux or Mac OS X, please see the
INSTALL file.


User Guide
----------

I will be trying to recreate the user guide sometime soon.

Copyright
---------

Luminotes Copyright (C) 2007-2008 Dan Helfman, 2013 John Osborne

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

See the COPYING file for more information. Also note that MochiKit has its
own separate license. See static/js/MochiKit_LICENSE.

Additionally, certain icons are from the Tango Destop Project
(http://tango.freedesktop.org), whose base icon theme is licensed under the
Creative Commons Attribution Share-Alike. For details, see:
http://creativecommons.org/licenses/by-sa/2.5/

The following icons fall into this category:
 * static/images/check.png
 * static/images/note_icon.png
 * static/images/file_icon.png
 * static/images/default_thumbnail.png
