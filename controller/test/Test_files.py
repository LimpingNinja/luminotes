import time
import types
from threading import Thread
from StringIO import StringIO
from Test_controller import Test_controller
from model.Notebook import Notebook
from model.Note import Note
from model.User import User
from model.Invite import Invite
from model.File import File
from controller.Notebooks import Access_error
import controller.Files
from controller.Files import Upload_file


class Test_files( Test_controller ):
  def setUp( self ):
    Test_controller.setUp( self )

    self.notebook = None
    self.anon_notebook = None
    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.username2 = u"deepthroat"
    self.password2 = u"mmmtobacco"
    self.email_address2 = u"parkinglot@example.com"
    self.user = None
    self.user2 = None
    self.anonymous = None
    self.session_id = None
    self.file_id = "22"
    self.filename = "file.png"
    self.file_data = "foobar\x07`-=[]\;',./~!@#$%^&*()_+{}|:\"<>?" * 100
    self.content_type = "image/png"

    # make Upload_file deal in fake files rather than actually using the filesystem
    Upload_file.fake_files = {} # map of file_id to fake file object

    @staticmethod
    def open_file( file_id, mode = None ):
      fake_file = Upload_file.fake_files.get( file_id )

      if fake_file:
        return fake_file

      if mode not in ( "w", "w+" ):
        raise IOError()

      fake_file = StringIO()
      Upload_file.fake_files[ file_id ] = fake_file
      return fake_file

    @staticmethod
    def delete_file( file_id ):
      fake_file = Upload_file.fake_files.get( file_id )

      if fake_file is None:
        raise IOError()

      del( Upload_file.fake_files[ file_id ] )

    @staticmethod
    def exists( file_id ):
      fake_file = Upload_file.fake_files.get( file_id )

      return fake_file is not None

    def close( self ):
      self.complete()

    Upload_file.open_file = open_file
    Upload_file.delete_file = delete_file
    Upload_file.exists = exists
    Upload_file.close = close

    self.make_users()
    self.make_notebooks()
    self.database.commit()

  def make_notebooks( self ):
    user_id = self.user.object_id

    self.trash = Notebook.create( self.database.next_id( Notebook ), u"trash", user_id = user_id )
    self.database.save( self.trash, commit = False )
    self.notebook = Notebook.create( self.database.next_id( Notebook ), u"notebook", self.trash.object_id, user_id = user_id )
    self.database.save( self.notebook, commit = False )

    note_id = self.database.next_id( Note )
    self.note = Note.create( note_id, u"<h3>my title</h3>blah", notebook_id = self.notebook.object_id, startup = True, user_id = user_id )
    self.database.save( self.note, commit = False )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon_notebook", user_id = user_id )
    self.database.save( self.anon_notebook, commit = False )

    self.database.execute( self.user.sql_save_notebook( self.notebook.object_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = True ) )
    self.database.execute( self.user.sql_save_notebook( self.anon_notebook.object_id, read_write = False, owner = False ) )

  def make_users( self ):
    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.user2.rate_plan = 1
    self.database.save( self.user2, commit = False )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )

  def test_download( self ):
    raise NotImplementedError()

  def test_upload_page( self ):
    self.login()

    result = self.http_get(
      "/files/upload_page?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
      session_id = self.session_id,
    )

    assert result.get( u"notebook_id" ) == self.notebook.object_id
    assert result.get( u"note_id" ) == self.note.object_id
    assert result.get( u"file_id" )

  def test_upload_page_without_login( self ):
    result = self.http_get(
      "/files/upload_page?notebook_id=%s&note_id=%s" % ( self.notebook.object_id, self.note.object_id ),
    )

    assert u"access" in result.get( u"error" )

  def test_upload( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    assert u"body" not in result
    assert u"script" not in result

    # assert that the file metadata was actually stored in the database
    db_file = self.database.load( File, self.file_id )
    assert db_file
    assert db_file.notebook_id == self.notebook.object_id
    assert db_file.note_id == self.note.object_id
    assert db_file.filename == self.filename
    assert db_file.size_bytes == len( self.file_data )
    assert db_file.content_type == self.content_type

    # assert that the file data was actually stored
    assert Upload_file.open_file( self.file_id ).read() == self.file_data

    # assert that storage bytes increased
    orig_storage_bytes = self.user.storage_bytes
    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes > orig_storage_bytes

  def test_upload_without_login( self ):
    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
    )

    assert u"access" in result.get( u"script" )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_without_access( self ):
    self.login2()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id
    )

    assert u"access" in result.get( u"script" )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_without_file_id( self ):
    self.login()

    result = self.http_upload(
      "/files/upload",
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id
    )

    assert u"error" in result[ u"body" ][ 0 ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_unnamed( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = "",
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id
    )

    assert "select a file" in result[ "script" ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_invalid_content_length( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      headers = [ ( "Content-Length", "-10" ) ],
      session_id = self.session_id
    )

    assert u"error" in result[ u"body" ][ 0 ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_cancel( self ):
    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      simulate_cancel = True,
      session_id = self.session_id
    )

    assert u"body" not in result
    assert u"script" not in result

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def test_upload_over_quota( self ):
    large_file_data = self.file_data * 5

    self.login()

    result = self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = large_file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    assert "quota" in result[ "script" ]

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

  def assert_streaming_error( self, result, error_string ):
    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    found_error = False

    try:
      for piece in gen:
        if error_string in piece:
          found_error = True
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    assert found_error

  def test_progress( self ):
    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

    self.login2()
    self.database.save( File( object_id = self.file_id ) )

    # start a file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?file_id=%s" % self.file_id,
        dict(
          notebook_id = self.notebook.object_id,
          note_id = self.note.object_id,
        ),
        filename = self.filename,
        file_data = self.file_data * 1000,
        content_type = self.content_type,
        session_id = self.session_id,
      )

    Thread( target = upload ).start()

    # report on that file's upload progress
    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    tick_count = 0
    tick_done = False
    complete = False

    try:
      for piece in gen:
        if u"tick(" in piece:
          tick_count += 1
        if u"tick(1.0)" in piece:
          tick_done = True
        if u"complete" in piece:
          complete = True
    # during this unit test, full session info isn't available, so swallow an expected
    # exception about session_storage
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    # assert that the progress bar is moving, and then completes
    assert tick_count >= 2
    assert tick_done
    assert complete

  def test_progress_without_login( self ):
    self.database.execute( self.user2.sql_save_notebook( self.notebook.object_id, read_write = True, owner = False ) )
    self.database.execute( self.user2.sql_save_notebook( self.notebook.trash_id, read_write = True, owner = False ) )

    self.login2() # this login is for the upload, not the call to progress
    self.database.save( File( object_id = self.file_id ) )

    # start a file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?file_id=%s" % self.file_id,
        dict(
          notebook_id = self.notebook.object_id,
          note_id = self.note.object_id,
        ),
        filename = self.filename,
        file_data = self.file_data * 1000,
        content_type = self.content_type,
        session_id = self.session_id,
      )

    Thread( target = upload ).start()

    # report on that file's upload progress
    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
    )

    print u"access" in result[ u"body" ][ 0 ]

  def test_progress_for_completed_upload( self ):
    self.login()
    self.database.save( File( object_id = self.file_id ) )

    # upload a file completely
    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    # report on that completed file's upload progress
    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    gen = result[ u"body" ]
    assert isinstance( gen, types.GeneratorType )

    complete = False

    try:
      for piece in gen:
        if u"complete" in piece:
          complete = True
    # during this unit test, full session info isn't available, so swallow an expected
    # exception about session_storage
    except AttributeError, exc:
      if u"session_storage" not in str( exc ):
        raise exc

    # assert that the progress bar is moving, and then completes
    assert complete

  def test_progress_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    assert u"error" in result[ u"body" ][ 0 ]
    assert u"unknown" in result[ u"body" ][ 0 ]

  def test_progress_over_quota( self ):
    self.login()
    self.database.save( File( object_id = self.file_id ) )

    # start a large file uploading in a separate thread
    def upload():
      self.http_upload(
        "/files/upload?file_id=%s" % self.file_id,
        dict(
          notebook_id = self.notebook.object_id,
          note_id = self.note.object_id,
        ),
        filename = self.filename,
        file_data = self.file_data * 1000,
        content_type = self.content_type,
        session_id = self.session_id,
      )

    Thread( target = upload ).start()

    result = self.http_get(
      "/files/progress?file_id=%s&filename=%s" % ( self.file_id, self.filename ),
      session_id = self.session_id,
    )

    self.assert_streaming_error( result, u"quota" )

  def test_stats( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert result[ u"filename" ] == self.filename
    assert result[ u"size_bytes" ] == len( self.file_data )

    orig_storage_bytes = self.user.storage_bytes
    user = self.database.load( User, self.user.object_id )
    assert result[ u"storage_bytes" ] == user.storage_bytes
    assert user.storage_bytes > orig_storage_bytes

  def test_stats_without_login( self ):
    self.login() # this login is for the upload, not the call to stats

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
    )

    assert u"access" in result[ u"error" ]

  def test_stats_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2() # now login as a different user

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_stats_with_unknown_file_id( self ):
    self.login()

    result = self.http_get(
      "/files/stats?file_id=%s" % self.file_id,
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_delete( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    db_file = self.database.load( File, self.file_id )
    assert db_file is None
    assert not Upload_file.exists( self.file_id )

    orig_storage_bytes = self.user.storage_bytes
    user = self.database.load( User, self.user.object_id )
    assert result[ u"storage_bytes" ] == user.storage_bytes
    assert user.storage_bytes != orig_storage_bytes

  def test_delete_without_login( self ):
    self.login() # this login is for the upload, not the call to delete

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
    )

    assert u"access" in result[ u"error" ]

  def test_delete_without_access( self ):
    self.login()

    self.http_upload(
      "/files/upload?file_id=%s" % self.file_id,
      dict(
        notebook_id = self.notebook.object_id,
        note_id = self.note.object_id,
      ),
      filename = self.filename,
      file_data = self.file_data,
      content_type = self.content_type,
      session_id = self.session_id,
    )

    self.login2() # now login as a different user

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_delete_with_unknown_file_id( self ):
    self.login()

    result = self.http_post(
      "/files/delete",
      dict(
        file_id = self.file_id,
      ),
      session_id = self.session_id,
    )

    assert u"access" in result[ u"error" ]

  def test_rename( self ):
    raise NotImplementedError()

  def test_purge_unused( self ):
    raise NotImplementedError()

  def login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]

  def login2( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username2,
      password = self.password2,
      login_button = u"login",
    ) )
    self.session_id = result[ u"session_id" ]