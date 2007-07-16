#!/usr/bin/python2.4

import os
import os.path
from controller.Database import Database
from controller.Scheduler import Scheduler
from model.Entry import Entry


class Initializer( object ):
  HTML_PATH = u"static/html"
  ENTRY_FILES = [ # the second element of the tuple is whether to show the entry on startup
    #( u"navigation.html", True ), # skip for now, since the navigtaion entry doesn't have a title
    ( u"about.html", True ),
    ( u"features.html", True ),
    ( u"take a tour.html", False ),
    ( u"try it out.html", False ),
    ( u"login.html", False ),
    ( u"password reset.html", False ),
    ( u"supported browsers.html", False ),
    ( u"advanced browser features.html", False ),
  ]

  def __init__( self, scheduler, database ):
    self.scheduler = scheduler
    self.database = database

    threads = (
      self.update_main_notebook(),
    )

    for thread in threads:
      self.scheduler.add( thread )
      self.scheduler.wait_for( thread )

  def update_main_notebook( self ):
    self.database.load( u"anonymous", self.scheduler.thread )
    anonymous = ( yield Scheduler.SLEEP )
    main_notebook = anonymous.notebooks[ 0 ]._Read_only_notebook__wrapped
    startup_entries = []

    # update all of the entries in the main notebook
    for ( filename, startup ) in self.ENTRY_FILES:
      full_filename = os.path.join( self.HTML_PATH, filename )
      contents = file( full_filename ).read()

      title = filename.replace( u".html", u"" )
      entry = main_notebook.lookup_entry_by_title( title )

      if entry:
        main_notebook.update_entry( entry, contents )
      # if for some reason the entry isn't present, create it
      else:
        self.database.next_id( self.scheduler.thread )
        entry_id = ( yield Scheduler.SLEEP )
        entry = Entry( entry_id, contents )
        main_notebook.add_entry( entry )

      main_notebook.remove_startup_entry( entry )
      if startup:
        startup_entries.append( entry )

    for entry in startup_entries:
      main_notebook.add_startup_entry( entry )

    main_notebook.name = u"Luminotes"
    self.database.save( main_notebook )


def main():
  scheduler = Scheduler()
  database = Database( scheduler, "data.db" )
  initializer = Initializer( scheduler, database )
  scheduler.wait_until_idle()


if __name__ == "__main__":
  main()
