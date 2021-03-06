#!/usr/bin/python2.4

import os
import os.path
from config.Common import settings
from controller.Database import Database
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from tools.initdb import fix_note_contents


class Updater( object ):
  HTML_PATH = u"static/html"
  NOTE_FILES = [ # the second element of the tuple is whether to show the note on startup
    ( u"sign up.html", False ),
    ( u"faq.html", False ),
    ( u"meet the team.html", False ),
    ( u"contact info.html", False ),
    ( u"login.html", False ),
    ( u"source code.html", False ),
    ( u"password reset.html", False ),
    ( u"advanced browser features.html", False ),
    ( u"supported browsers.html", False ),
    ( u"community.html", False ),
    ( u"enable JavaScript.html", False ),
  ]

  def __init__( self, database, settings ):
    self.database = database
    self.settings = settings

    self.update_main_notebook()
    self.database.commit()

  def update_main_notebook( self ):
    anonymous = self.database.select_one( User, User.sql_load_by_username( u"anonymous" ) )
    main_notebook = self.database.select_one( Notebook, anonymous.sql_load_notebooks() )

    # get the id for each note
    note_ids = {}
    for ( filename, startup ) in self.NOTE_FILES:
      title = filename.replace( u".html", u"" )
      note = self.database.select_one( Note, main_notebook.sql_load_note_by_title( title ) )

      if note is not None:
        note_ids[ filename ] = note.object_id

    # update all of the notes in the main notebook
    for ( filename, startup ) in self.NOTE_FILES:
      title = filename.replace( u".html", u"" )
      note = self.database.select_one( Note, main_notebook.sql_load_note_by_title( title ) )
      self.update_note( filename, startup, main_notebook, note_ids, note )

    if main_notebook.name != u"Luminotes":
      main_notebook.name = u"Luminotes"
      self.database.save( main_notebook, commit = False )

  def update_note( self, filename, startup, main_notebook, note_ids, note = None ):
    full_filename = os.path.join( self.HTML_PATH, filename )
    contents = fix_note_contents( file( full_filename ).read(), main_notebook.object_id, note_ids, self.settings )

    if note:
      if note.contents == contents:
        return
      note.contents = contents
    # if for some reason the note isn't present, create it
    else:
      next_id = self.database.next_id( Note )
      note = Note.create( next_id, contents, notebook_id = main_notebook.object_id, startup = startup )

    self.database.save( note, commit = False )

def main( args ):
  import cherrypy
  from config import Common

  cherrypy.config.update( Common.settings )

  if args and "-d" in args:
    from config import Development
    settings = Development.settings
  elif args and "-l" in args:
    from config import Desktop
    settings = Desktop.settings
  else:
    from config import Production
    settings = Production.settings

  cherrypy.config.update( settings )

  database = Database(
    host = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_host" ),
    ssl_mode = cherrypy.config.configMap[ u"global" ].get( u"luminotes.db_ssl_mode" ),
    data_dir = ".",
  )
  initializer = Updater( database, cherrypy.config.configMap )


if __name__ == "__main__":
  import sys
  main( sys.argv[ 1: ] )
