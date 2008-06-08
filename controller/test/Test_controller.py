import smtplib
import cherrypy
from Stub_database import Stub_database
from Stub_view import Stub_view
from Stub_smtp import Stub_smtp
from config import Common
from datetime import datetime
from StringIO import StringIO
from copy import copy


class Wrapped_StringIO( StringIO ):
  """
  A wrapper for StringIO that includes a bytes_read property, needed to work with
  controller.Files.Upload_file.
  """
  bytes_read = property( lambda self: self.tell() )


class Truncated_StringIO( Wrapped_StringIO ):
  """
  A wrapper for Wrapped_StringIO that forcibly closes the file when only some of it has been read.
  Used for simulating an upload that is canceled part of the way through.
  """
  def readline( self, size = None ):
    if self.tell() >= len( self.getvalue() ) * 0.25:
      self.close()
      return ""

    return Wrapped_StringIO.readline( self, 256 )


class Test_controller( object ):
  def __init__( self ):
    from model.User import User
    from model.Group import Group
    from model.Notebook import Notebook
    from model.Note import Note
    from model.Invite import Invite
    from model.User_revision import User_revision
    from model.File import File

    # Since Stub_database isn't a real database and doesn't know SQL, replace some of the
    # SQL-returning methods in User, Note, and Notebook to return functions that manipulate data in
    # Stub_database directly instead. This is all a little fragile, but it's better than relying on
    # the presence of a real database for unit tests.
    def sql_save_notebook( self, notebook_id, read_write, owner, rank, database ):
      if self.object_id in database.user_notebook:
        database.user_notebook[ self.object_id ].append( ( notebook_id, read_write, owner, rank ) )
      else:
        database.user_notebook[ self.object_id ] = [ ( notebook_id, read_write, owner, rank ) ]

    User.sql_save_notebook = lambda self, notebook_id, read_write = False, owner = False, rank = None: \
      lambda database: sql_save_notebook( self, notebook_id, read_write, owner, rank, database )

    def sql_remove_notebook( self, notebook_id, database ):
      if self.object_id in database.user_notebook:
        for notebook_info in database.user_notebook[ self.object_id ]:
          if notebook_info[ 0 ] == notebook_id:
            database.user_notebook[ self.object_id ].remove( notebook_info )

    User.sql_remove_notebook = lambda self, notebook_id: \
      lambda database: sql_remove_notebook( self, notebook_id, database )

    def sql_load_notebooks( self, parents_only, undeleted_only, read_write, database ):
      notebooks = []
      notebook_infos = database.user_notebook.get( self.object_id )

      if not notebook_infos: return []

      for notebook_info in notebook_infos:
        ( notebook_id, notebook_read_write, owner, rank ) = notebook_info
        notebook = database.objects.get( notebook_id )[ -1 ]
        notebook.read_write = notebook_read_write
        notebook.owner = owner
        notebook.rank = rank
        if parents_only and notebook.trash_id is None:
          continue
        if undeleted_only and notebook.deleted is True:
          continue
        if read_write and notebook_read_write is False:
          continue
        notebooks.append( notebook )

      notebooks.sort( lambda a, b: a.rank is None and 1 or cmp( a.rank, b.rank ) )

      return notebooks

    User.sql_load_notebooks = lambda self, parents_only = False, undeleted_only = False, read_write = False: \
      lambda database: sql_load_notebooks( self, parents_only, undeleted_only, read_write, database )

    def sql_load_by_username( username, database ):
      users = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, User ) and obj.username == username:
          users.append( obj )

      return users

    User.sql_load_by_username = staticmethod( lambda username: \
      lambda database: sql_load_by_username( username, database ) )

    def sql_load_by_email_address( email_address, database ):
      users = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, User ) and obj.email_address == email_address:
          users.append( obj )

      return users

    User.sql_load_by_email_address = staticmethod( lambda email_address: \
      lambda database: sql_load_by_email_address( email_address, database ) )

    def sql_calculate_storage( self, database ):
      return ( 17, 3, 4, 22 ) # rather than actually calculating anything, return arbitrary numbers

    User.sql_calculate_storage = lambda self: \
      lambda database: sql_calculate_storage( self, database )

    def sql_calculate_group_storage( self, database ):
      return ( 0, 0 )

    User.sql_calculate_group_storage = lambda self: \
      lambda database: sql_calculate_group_storage( self, database )

    def sql_has_access( self, notebook_id, read_write, owner, database ):
      for ( user_id, notebook_infos ) in database.user_notebook.items():
        for notebook_info in notebook_infos:
          ( db_notebook_id, db_read_write, db_owner, rank ) = notebook_info

          if self.object_id == user_id and notebook_id == db_notebook_id:
            if read_write is True and db_read_write is False:
              return False
            if owner is True and db_owner is False:
              return False
            return True

      return False

    User.sql_has_access = lambda self, notebook_id, read_write = False, owner = False: \
      lambda database: sql_has_access( self, notebook_id, read_write, owner, database )

    def sql_update_access( self, notebook_id, read_write, owner, database ):
      for ( user_id, notebook_infos ) in database.user_notebook.items():
        for notebook_info in notebook_infos:
          ( db_notebook_id, db_read_write, db_owner, rank ) = notebook_info

          if self.object_id == user_id and notebook_id == db_notebook_id:
            notebook_infos_copy = list( notebook_infos )
            notebook_infos_copy.remove( notebook_info )
            notebook_infos_copy.append( ( notebook_id, read_write, owner, rank ) )
            database.user_notebook[ user_id ] = notebook_infos_copy

    User.sql_update_access = lambda self, notebook_id, read_write = False, owner = False: \
      lambda database: sql_update_access( self, notebook_id, read_write, owner, database )

    def sql_update_notebook_rank( self, notebook_id, rank, database ):
      max_rank = -1

      for ( user_id, notebook_infos ) in database.user_notebook.items():
        for notebook_info in notebook_infos:
          ( db_notebook_id, db_read_write, db_owner, db_rank ) = notebook_info

          if self.object_id == user_id and notebook_id == db_notebook_id:
            notebook_infos_copy = list( notebook_infos )
            notebook_infos_copy.remove( notebook_info )
            notebook_infos_copy.append( ( db_notebook_id, db_read_write, db_owner, rank ) )
            database.user_notebook[ user_id ] = notebook_infos_copy

    User.sql_update_notebook_rank = lambda self, notebook_id, rank: \
      lambda database: sql_update_notebook_rank( self, notebook_id, rank, database )

    def sql_highest_notebook_rank( self, database ):
      max_rank = -1

      for ( user_id, notebook_infos ) in database.user_notebook.items():
        for notebook_info in notebook_infos:
          ( db_notebook_id, db_read_write, db_owner, db_rank ) = notebook_info
          if self.object_id == user_id and db_rank > max_rank:
            max_rank = db_rank

      return max_rank

    User.sql_highest_notebook_rank = lambda self: \
      lambda database: sql_highest_notebook_rank( self, database )

    def sql_load_groups( self, database ):
      groups = []
      group_infos = database.user_group.get( self.object_id )

      if not group_infos: return []

      for group_info in group_infos:
        ( group_id, admin ) = group_info
        group = database.objects.get( group_id )[ -1 ]
        group.admin = admin
        groups.append( group )

      groups.sort( lambda a, b: cmp( a.name, b.name ) )

      return groups

    User.sql_load_groups = lambda self: \
      lambda database: sql_load_groups( self, database )

    def sql_save_group( self, group_id, admin, database ):
      if self.object_id in database.user_group:
        database.user_group[ self.object_id ].append( ( group_id, admin ) )
      else:
        database.user_group[ self.object_id ] = [ ( group_id, admin ) ]

    User.sql_save_group = lambda self, group_id, admin = False: \
      lambda database: sql_save_group( self, group_id, admin, database )

    def sql_remove_group( self, group_id, database ):
      for ( user_id, group_infos ) in database.user_group.items():
        for group_info in group_infos:
          ( db_group_id, db_admin ) = group_info

          if self.object_id == user_id and group_id == db_group_id:
            database.user_group[ user_id ].remove( group_info )

    User.sql_remove_group = lambda self, group_id: \
      lambda database: sql_remove_group( self, group_id, database )

    def sql_in_group( self, group_id, admin, database ):
      for ( user_id, group_infos ) in database.user_group.items():
        for group_info in group_infos:
          ( db_group_id, db_admin ) = group_info

          if self.object_id == user_id and group_id == db_group_id:
            if admin is True and db_admin is False:
              return False

            return True

      return False

    User.sql_in_group = lambda self, group_id, admin = False: \
      lambda database: sql_in_group( self, group_id, admin, database )

    def sql_revoke_invite_access( notebook_id, trash_id, email_address, database ):
      invites = []

      for ( user_id, notebook_infos ) in database.user_notebook.items():
        for notebook_info in list( notebook_infos ):
          ( db_notebook_id, read_write, owner, rank ) = notebook_info
          if db_notebook_id not in ( notebook_id, trash_id ): continue
          for ( object_id, obj_list ) in database.objects.items():
            obj = obj_list[ -1 ]
            if isinstance( obj, Invite ) and obj.notebook_id == notebook_id and \
               obj.email_address == email_address:
              database.user_notebook[ user_id ].remove( notebook_info )

    User.sql_revoke_invite_access = staticmethod( lambda notebook_id, trash_id, email_address: \
      lambda database: sql_revoke_invite_access( notebook_id, trash_id, email_address, database ) )

    def sql_load_users( self, admin, database ):
      users = []

      for ( user_id, group_infos ) in database.user_group.items():
        for group_info in group_infos:
          ( db_group_id, db_admin ) = group_info

          if db_group_id != self.object_id: continue
          if admin is True and db_admin != True: continue
          if admin is False and db_admin != False: continue

          user = database.objects.get( user_id )[ -1 ]
          users.append( user )

      users.sort( lambda a, b: cmp( a.username, b.username ) )

      return users

    Group.sql_load_users = lambda self, admin = None: \
      lambda database: sql_load_users( self, admin, database )

    def sql_load_revisions( self, database ):
      note_list = database.objects.get( self.object_id )
      if not note_list: return None
      revisions = []

      for note in note_list:
        user_list = database.objects.get( note.user_id )
        user_id = None
        username = None 

        if user_list:
          user_id = user_list[ -1 ].object_id
          username = user_list[ -1 ].username

        revisions.append( User_revision( note.revision, user_id, username ) )

      return revisions

    Note.sql_load_revisions = lambda self: \
      lambda database: sql_load_revisions( self, database )

    def sql_load_notes( self, start, count, database ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id:
          notes.append( obj )

      notes.sort( lambda a, b: -cmp( a.revision, b.revision ) )
      if count is None:
        return notes[ start : ]
      else:
        return notes[ start : start + count ]

    Notebook.sql_load_notes = lambda self, start = 0, count = None: \
      lambda database: sql_load_notes( self, start, count, database )

    def sql_load_startup_notes( self, database ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and obj.startup:
          notes.append( obj )

      return notes

    Notebook.sql_load_startup_notes = lambda self: \
      lambda database: sql_load_startup_notes( self, database )

    def sql_load_recent_notes( self, database, start, count ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id:
          obj = copy( obj )
          obj._Note__creation = database.objects[ object_id ][ 0 ].revision
          notes.append( obj )

      notes.sort( lambda a, b: -cmp( a.creation, b.creation ) )
      notes = notes[ start : start + count ]
      return notes

    Notebook.sql_load_recent_notes = lambda self, start = 0, count = 10: \
      lambda database: sql_load_recent_notes( self, database, start, count )

    def sql_load_note_by_title( self, title, database ):
      notes = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and obj.title == title:
          notes.append( obj )

      return notes

    Notebook.sql_load_note_by_title = lambda self, title: \
      lambda database: sql_load_note_by_title( self, title, database )

    def sql_search_notes( user_id, first_notebook_id, search_text, database ):
      first_notes = []
      other_notes = []
      search_text = search_text.lower()

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]

        if not isinstance( obj, Note ):
          continue

        if user_id in database.user_notebook:
          for notebook_info in database.user_notebook[ user_id ]:
            if notebook_info[ 0 ] != obj.notebook_id:
              continue

        if obj.deleted_from_id == None and \
           search_text in obj.contents.lower():
          if obj.notebook_id == first_notebook_id:
            first_notes.append( obj )
          else:
            other_notes.append( obj )

      return first_notes + other_notes

    Notebook.sql_search_notes = staticmethod( lambda user_id, first_notebook_id, search_text: \
      lambda database: sql_search_notes( user_id, first_notebook_id, search_text, database ) )

    def sql_highest_note_rank( self, database ):
      max_rank = -1

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id and obj.rank > max_rank:
          max_rank = obj.rank

      return max_rank

    Notebook.sql_highest_note_rank = lambda self: \
      lambda database: sql_highest_note_rank( self, database )

    def sql_count_notes( self, database ):
      count = 0

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Note ) and obj.notebook_id == self.object_id:
          count += 1

      return count

    Notebook.sql_count_notes = lambda self: \
      lambda database: sql_count_notes( self, database )

    def sql_load_similar( self, database ):
      invites = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Invite ) and obj.notebook_id == self.notebook_id and \
           obj.email_address == self.email_address and \
           obj.object_id != self.object_id:
          invites.append( obj )

      return invites

    Invite.sql_load_similar = lambda self: \
      lambda database: sql_load_similar( self, database )

    def sql_load_notebook_invites( notebook_id, database ):
      invites = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Invite ) and obj.notebook_id == notebook_id and \
           obj.email_address not in [ i.email_address for i in invites ]:
          invites.append( obj )

      return invites

    Invite.sql_load_notebook_invites = staticmethod( lambda notebook_id:
      lambda database: sql_load_notebook_invites( notebook_id, database ) )

    def sql_revoke_invites( self, database ):
      invites = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, Invite ) and obj.notebook_id == self.notebook_id and \
           obj.email_address == self.email_address:
          del( database.objects[ object_id ] )

    Invite.sql_revoke_invites = lambda self: \
      lambda database: sql_revoke_invites( self, database )

    def sql_load_note_files( note_id, database ):
      files = []

      for ( object_id, obj_list ) in database.objects.items():
        obj = obj_list[ -1 ]
        if isinstance( obj, File ) and obj.note_id == note_id:
          files.append( obj )

      return files

    File.sql_load_note_files = staticmethod( lambda note_id:
      lambda database: sql_load_note_files( note_id, database ) )

    def sql_delete( self, database ):
      del( database.objects[ self.object_id ] )

    File.sql_delete = lambda self: \
      lambda database: sql_delete( self, database )


  def setUp( self ):
    # trick tested methods into using a fake SMTP server
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    from controller.Root import Root
    cherrypy.lowercase_api = True
    self.database = Stub_database()
    self.settings = {
      u"global": {
        u"server.environment": "production",
        u"session_filter.on": True,
        u"session_filter.storage_type": u"ram",
        u"session_filter.locking": "implicit",
        u"encoding_filter.on": True,
        u"encoding_filter.encoding": "utf-8",
        u"decoding_filter.on": True,
        u"decoding_filter.encoding": "utf-8",
        u"server.log_to_screen": False,
        u"luminotes.http_url" : u"http://luminotes.com",
        u"luminotes.https_url" : u"https://luminotes.com",
        u"luminotes.http_proxy_ip" : u"127.0.0.1",
        u"luminotes.https_proxy_ip" : u"127.0.0.2",
        u"luminotes.support_email": "unittest@luminotes.com",
        u"luminotes.payment_email": "unittest@luminotes.com",
        u"luminotes.rate_plans": [
          {
            u"name": u"super",
            u"storage_quota_bytes": 1337 * 10,
            u"notebook_collaboration": False,
            u"user_admin": False,
            u"included_users": 1,
            u"fee": 1.99,
            u"yearly_fee": 19.90,
            u"button": u"[subscribe here user %s!] button",
            u"yearly_button": u"[yearly subscribe here user %s!] button",
          },
          {
            u"name": "extra super",
            u"storage_quota_bytes": 31337 * 1000,
            u"notebook_collaboration": True,
            u"user_admin": True,
            u"included_users": 3,
            u"fee": 9.00,
            u"yearly_fee": 90.00,
            u"button": u"[or here user %s!] button",
            u"yearly_button": u"[yearly or here user %s!] button",
          },
        ],
      },
      u"/files/download": {
        u"stream_response": True,
        u"encoding_filter.on": False,
      },
      u"/files/progress": {
        u"stream_response": True,
      },
    }

    cherrypy.root = Root( self.database, self.settings, suppress_exceptions = True )
    cherrypy.config.update( self.settings )
    cherrypy.server.start( init_only = True, server_class = None )

    # since we only want to test the controller, use the stub view for all exposed methods
    import controller.Expose
    Stub_view.result = None
    controller.Expose.view_override = Stub_view

  def tearDown( self ):
    cherrypy.server.stop()

  def http_get( self, http_path, headers = None, session_id = None, pretend_https = False ):
    """
    Perform an HTTP GET with the given path on the test server. Return the result dict as returned
    by the invoked method.
    """
    if headers is None:
      headers = []

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    if pretend_https:
      proxy_ip = self.settings[ "global" ].get( u"luminotes.https_proxy_ip" )
    else:
      proxy_ip = self.settings[ "global" ].get( u"luminotes.http_proxy_ip" )

    request = cherrypy.server.request( ( proxy_ip, 1234 ), u"127.0.0.5" )
    response = request.run( "GET %s HTTP/1.0" % str( http_path ), headers = headers, rfile = StringIO() )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
        Stub_view.result = None
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()

  def http_post( self, http_path, form_args, headers = None, session_id = None ):
    """
    Perform an HTTP POST with the given path on the test server, sending the provided form_args
    dict. Return the result dict as returned by the invoked method.
    """
    from urllib import urlencode
    post_data = urlencode( form_args )

    if headers is None:
      headers = []

    headers.extend( [
      ( u"Content-Type", u"application/x-www-form-urlencoded" ),
      ( u"Content-Length", unicode( len( post_data ) ) ),
    ] )

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    request = cherrypy.server.request( ( u"127.0.0.1", 1234 ), u"127.0.0.5" )
    response = request.run( "POST %s HTTP/1.0" % str( http_path ), headers = headers, rfile = StringIO( post_data ) )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
        Stub_view.result = None
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()

  def http_upload( self, http_path, form_args, filename, file_data, content_type, simulate_cancel = False, headers = None, session_id = None ):
    """
    Perform an HTTP POST with the given path on the test server, sending the provided form_args
    and file_data as a multipart form file upload. Return the result dict as returned by the
    invoked method.
    """
    boundary = "boundarygoeshere"
    post_data = [ "--%s\n" % boundary ]

    for ( name, value ) in form_args.items():
      post_data.append( 'Content-Disposition: form-data; name="%s"\n\n%s\n--%s\n' % (
        str( name ), str( value ), boundary
      ) )

    post_data.append( 'Content-Disposition: form-data; name="upload"; filename="%s"\n' % (
      filename.encode( "utf8" )
    ) )
    post_data.append( "Content-Type: %s\nContent-Transfer-Encoding: binary\n\n%s\n--%s--\n" % (
      content_type, file_data, boundary
    ) )

    if headers is None:
      headers = []

    post_data = "".join( post_data )
    headers.append( ( "Content-Type", "multipart/form-data; boundary=%s" % boundary ) )

    if "Content-Length" not in [ name for ( name, value ) in headers ]:
      headers.append( ( "Content-Length", str( len( post_data ) ) ) )

    if session_id:
      headers.append( ( u"Cookie", "session_id=%s" % session_id ) ) # will break if unicode is used for the value

    if simulate_cancel:
      file_wrapper = Truncated_StringIO( post_data )
    else:
      file_wrapper = Wrapped_StringIO( post_data )

    request = cherrypy.server.request( ( u"127.0.0.1", 1234 ), u"127.0.0.5" )
    response = request.run( "POST %s HTTP/1.0" % str( http_path ), headers = headers, rfile = file_wrapper )
    session_id = response.simple_cookie.get( u"session_id" )
    if session_id: session_id = session_id.value

    try:
      if Stub_view.result is not None:
        result = Stub_view.result
        Stub_view.result = None
      else:
        result = dict(
          status = response.status,
          headers = response.headers,
          body = response.body,
        )

      result[ u"session_id" ] = session_id
      return result
    finally:
      request.close()
