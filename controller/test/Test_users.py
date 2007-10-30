import re
import cherrypy
import smtplib
from pytz import utc
from nose.tools import raises
from datetime import datetime, timedelta
from nose.tools import raises
from Test_controller import Test_controller
from Stub_smtp import Stub_smtp
from model.User import User
from model.Notebook import Notebook
from model.Note import Note
from model.Password_reset import Password_reset
from controller.Users import Access_error


class Test_users( Test_controller ):
  RESET_LINK_PATTERN = re.compile( "(https?://\S+)?/r/(\S+)" )

  def setUp( self ):
    Test_controller.setUp( self )

    self.username = u"mulder"
    self.password = u"trustno1"
    self.email_address = u"outthere@example.com"
    self.new_username = u"reynolds"
    self.new_password = u"shiny"
    self.new_email_address = u"capn@example.com"
    self.username2 = u"scully"
    self.password2 = u"trustsome1"
    self.email_address2 = u"outthere@example.com"
    self.user = None
    self.user2 = None
    self.anonymous = None
    self.notebooks = None

    self.make_users()

  def make_users( self ):
    notebook_id1 = self.database.next_id( Notebook )
    notebook_id2 = self.database.next_id( Notebook )
    trash_id1 = self.database.next_id( Notebook )
    trash_id2 = self.database.next_id( Notebook )

    self.notebooks = [
      Notebook.create( notebook_id1, u"my notebook", trash_id = trash_id1 ),
      Notebook.create( notebook_id2, u"my other notebook", trash_id = trash_id2 ),
    ]
    self.database.save( self.notebooks[ 0 ] )
    self.database.save( self.notebooks[ 1 ] )

    self.anon_notebook = Notebook.create( self.database.next_id( Notebook ), u"anon notebook" )
    self.database.save( self.anon_notebook )
    self.startup_note = Note.create(
      self.database.next_id( Note ), u"<h3>login</h3>",
      notebook_id = self.anon_notebook.object_id, startup = True,
    )
    self.database.save( self.startup_note )

    self.user = User.create( self.database.next_id( User ), self.username, self.password, self.email_address )
    self.database.save( self.user, commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook_id1, read_write = True ), commit = False )
    self.database.execute( self.user.sql_save_notebook( notebook_id2, read_write = True ), commit = False )

    self.user2 = User.create( self.database.next_id( User ), self.username2, self.password2, self.email_address2 )
    self.database.save( self.user2, commit = False )

    self.anonymous = User.create( self.database.next_id( User ), u"anonymous" )
    self.database.save( self.anonymous, commit = False )
    self.database.execute( self.anonymous.sql_save_notebook( self.anon_notebook.object_id ), commit = False )

    self.database.commit()

  def test_signup( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

  def test_current_after_signup( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password,
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    user = self.database.last_saved_obj
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    assert result[ u"user" ].object_id == user.object_id
    assert result[ u"user" ].username == self.new_username
    assert result[ u"user" ].email_address == self.new_email_address

    notebooks = result[ u"notebooks" ]
    notebook = notebooks[ 0 ]
    assert notebook.object_id == new_notebook_id
    assert notebook.revision
    assert notebook.name == u"my notebook"
    assert notebook.trash_id
    assert notebook.read_write == True

    notebook = notebooks[ 1 ]
    assert notebook.object_id == notebooks[ 0 ].trash_id
    assert notebook.revision
    assert notebook.name == u"trash"
    assert notebook.trash_id == None
    assert notebook.read_write == True

    notebook = notebooks[ 2 ]
    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.revision == self.anon_notebook.revision
    assert notebook.name == self.anon_notebook.name
    assert notebook.trash_id == None
    assert notebook.read_write == False

    assert result.get( u"login_url" ) is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337

  def test_signup_with_different_passwords( self ):
    result = self.http_post( "/users/signup", dict(
      username = self.new_username,
      password = self.new_password,
      password_repeat = self.new_password + u"nomatch",
      email_address = self.new_email_address,
      signup_button = u"sign up",
    ) )

    assert result[ u"error" ]

  def test_demo( self ):
    result = self.http_post( "/users/demo", dict() )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )

  def test_current_after_demo( self ):
    result = self.http_post( "/users/demo", dict() )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    user = self.database.last_saved_obj
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    assert result[ u"user" ].object_id == user.object_id
    assert result[ u"user" ].username is None
    assert result[ u"user" ].email_address is None

    notebooks = result[ u"notebooks" ]
    assert len( notebooks ) == 3
    notebook = notebooks[ 0 ]
    assert notebook.object_id == new_notebook_id
    assert notebook.revision
    assert notebook.name == u"my notebook"
    assert notebook.trash_id
    assert notebook.read_write == True

    notebook = notebooks[ 1 ]
    assert notebook.object_id == notebooks[ 0 ].trash_id
    assert notebook.revision
    assert notebook.name == u"trash"
    assert notebook.trash_id == None
    assert notebook.read_write == True

    notebook = notebooks[ 2 ]
    assert notebook.object_id == self.anon_notebook.object_id
    assert notebook.revision == self.anon_notebook.revision
    assert notebook.name == self.anon_notebook.name
    assert notebook.trash_id == None
    assert notebook.read_write == False

    assert result.get( u"login_url" ) is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337

  def test_current_after_demo_twice( self ):
    result = self.http_post( "/users/demo", dict() )
    session_id = result[ u"session_id" ]

    new_notebook_id = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    user = self.database.last_saved_obj
    assert isinstance( user, User )
    result = cherrypy.root.users.current( user.object_id )

    user_id = result[ u"user" ].object_id
    assert user_id == user.object_id

    # request a demo for a second time
    result = self.http_post( "/users/demo", dict(), session_id = session_id )

    assert result[ u"redirect" ].startswith( u"/notebooks/" )
    notebook_id_again = result[ u"redirect" ].split( u"/notebooks/" )[ -1 ]

    assert notebook_id_again == new_notebook_id

    result = cherrypy.root.users.current( user_id )

    user_id_again = result[ u"user" ].object_id

    # since we're already logged in as a guest user with a demo notebook, requesting a demo again
    # should just use the same guest user with the same notebook
    assert user_id_again == user_id

  def test_login( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = self.password,
      login_button = u"login",
    ) )

    assert result[ u"redirect" ] == u"/notebooks/%s" % self.notebooks[ 0 ].object_id

  def test_login_with_unknown_user( self ):
    result = self.http_post( "/users/login", dict(
      username = u"nosuchuser",
      password = self.password,
      login_button = u"login",
    ) )

    assert result[ u"error" ]

  def test_login_with_invalid_password( self ):
    result = self.http_post( "/users/login", dict(
      username = self.username,
      password = u"wrongpass",
      login_button = u"login",
    ) )

    assert result[ u"error" ]

  def test_logout( self ):
    result = self.http_post( "/users/logout", dict() )

    assert result[ u"redirect" ] == self.settings[ u"global" ].get( u"luminotes.http_url" ) + u"/"

  def test_current( self ):
    result = cherrypy.root.users.current( self.user.object_id )

    assert result[ u"user" ]
    assert result[ u"user" ].object_id == self.user.object_id
    assert result[ u"user" ].username == self.user.username
    assert len( result[ u"notebooks" ] ) == 3
    assert result[ u"notebooks" ][ 0 ].object_id == self.notebooks[ 0 ].object_id
    assert result[ u"notebooks" ][ 0 ].read_write == True
    assert result[ u"notebooks" ][ 1 ].object_id == self.notebooks[ 1 ].object_id
    assert result[ u"notebooks" ][ 1 ].read_write == True
    assert result[ u"notebooks" ][ 2 ].object_id == self.anon_notebook.object_id
    assert result[ u"notebooks" ][ 2 ].read_write == False
    assert result[ u"login_url" ] is None
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337

  def test_current_anonymous( self ):
    result = cherrypy.root.users.current( self.anonymous.object_id )

    assert result[ u"user" ].username == "anonymous"
    assert len( result[ u"notebooks" ] ) == 1
    assert result[ u"notebooks" ][ 0 ].object_id == self.anon_notebook.object_id
    assert result[ u"notebooks" ][ 0 ].name == self.anon_notebook.name
    assert result[ u"notebooks" ][ 0 ].read_write == False

    login_note = self.database.select_one( Note, self.anon_notebook.sql_load_note_by_title( u"login" ) )
    assert result[ u"login_url" ] == u"%s/notebooks/%s?note_id=%s" % (
      self.settings[ u"global" ][ u"luminotes.https_url" ],
      self.anon_notebook.object_id,
      login_note.object_id,
    )
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337

  def test_update_storage( self ):
    previous_revision = self.user.revision

    cherrypy.root.users.update_storage( self.user.object_id )

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    user = self.database.load( User, self.user.object_id )
    assert user.storage_bytes == expected_size
    assert user.revision > previous_revision

  def test_update_storage_with_unknown_user_id( self ):
    original_revision = self.user.revision

    cherrypy.root.users.update_storage( 77 )

    expected_size = cherrypy.root.users.calculate_storage( self.user )

    user = self.database.load( User, self.user.object_id )
    assert self.user.storage_bytes == 0
    assert self.user.revision == original_revision

  def test_send_reset( self ):
    # trick send_reset() into using a fake SMTP server
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    result = self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )
    session_id = result[ u"session_id" ]
    
    assert u"has been sent to" in result[ u"message" ]
    assert smtplib.SMTP.connected == False
    assert "<%s>" % self.settings[ u"global" ][ u"luminotes.support_email" ] in smtplib.SMTP.from_address
    assert smtplib.SMTP.to_addresses == [ self.user.email_address ]
    assert u"password reset" in smtplib.SMTP.message
    assert self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )

  def test_send_reset_to_unknown_email_address( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    result = self.http_post( "/users/send_reset", dict(
      email_address = u"unknown@example.com",
      send_reset_button = u"email me",
    ) )
    
    assert u"no Luminotes user" in result[ u"error" ]
    assert smtplib.SMTP.connected == False
    assert smtplib.SMTP.from_address == None
    assert smtplib.SMTP.to_addresses == None
    assert smtplib.SMTP.message == None

  def test_redeem_reset( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert result[ u"user" ].username == "anonymous"
    assert len( result[ u"notebooks" ] ) == 1
    assert result[ u"notebooks" ][ 0 ].object_id == self.anon_notebook.object_id
    assert result[ u"notebooks" ][ 0 ].name == self.anon_notebook.name
    assert result[ u"notebooks" ][ 0 ].read_write == False

    login_note = self.database.select_one( Note, self.anon_notebook.sql_load_note_by_title( u"login" ) )
    assert result[ u"login_url" ] == u"%s/notebooks/%s?note_id=%s" % (
      self.settings[ u"global" ][ u"luminotes.https_url" ],
      self.anon_notebook.object_id,
      login_note.object_id,
    )
    assert result[ u"logout_url" ] == self.settings[ u"global" ][ u"luminotes.https_url" ] + u"/"

    rate_plan = result[ u"rate_plan" ]
    assert rate_plan
    assert rate_plan[ u"name" ] == u"super"
    assert rate_plan[ u"storage_quota_bytes" ] == 1337

    assert result[ u"notebook" ].object_id == self.anon_notebook.object_id
    assert len( result[ u"startup_notes" ] ) == 1
    assert result[ u"startup_notes" ][ 0 ].object_id == self.startup_note.object_id
    assert result[ u"startup_notes" ][ 0 ].title == self.startup_note.title
    assert result[ u"startup_notes" ][ 0 ].contents == self.startup_note.contents
    assert result[ u"note_read_write" ] is False

    assert result[ u"notes" ]
    assert len( result[ u"notes" ] ) == 1
    assert result[ u"notes" ][ 0 ].title == u"complete your password reset"
    assert result[ u"notes" ][ 0 ].notebook_id == self.anon_notebook.object_id
    assert u"password reset" in result[ u"notes" ][ 0 ].contents
    assert self.user.username in result[ u"notes" ][ 0 ].contents
    assert self.user2.username in result[ u"notes" ][ 0 ].contents

  def test_redeem_reset_unknown( self ):
    password_reset_id = u"unknownresetid"
    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"expired" in result[ u"error" ]

  def test_redeem_reset_expired( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    # to trigger expiration, pretend that the password reset was made 25 hours ago
    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset._Persistent__revision = datetime.now( tz = utc ) - timedelta( hours = 25 )
    self.database.save( password_reset )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"expired" in result[ u"error" ]

  def test_redeem_reset_already_redeemed( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset.redeemed = True
    self.database.save( password_reset )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"already" in result[ u"error" ]

  def test_redeem_reset_unknown_email( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset._Password_reset__email_address = u"unknown@example.com"
    self.database.save( password_reset )

    result = self.http_get( "/users/redeem_reset/%s" % password_reset_id )

    assert u"email address" in result[ u"error" ]

  def test_reset_password( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    assert result[ u"redirect" ]

    # check that the password reset is now marked as redeemed
    password_reset = self.database.load( Password_reset, password_reset_id )
    assert password_reset.redeemed

    # check that the password was actually reset for one of the users, but not the other
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( new_password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_unknown_reset_id( self ):
    new_password = u"newpass"
    password_reset_id = u"unknownresetid"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    assert u"expired" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_invalid_reset_id( self ):
    new_password = u"newpass"
    password_reset_id = u"invalid reset id"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    assert u"valid" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_expired( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    # to trigger expiration, pretend that the password reset was made 25 hours ago
    password_reset = self.database.load( Password_reset, password_reset_id )
    password_reset._Persistent__revision = datetime.now( tz = utc ) - timedelta( hours = 25 )
    self.database.save( password_reset )

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    # check that the password reset is not marked as redeemed
    password_reset = self.database.load( Password_reset, password_reset_id )
    assert password_reset.redeemed == False

    assert u"expired" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_non_matching( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, u"nonmatchingpass" ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    assert u"password" in result[ "error" ]

    # check that neither user's password has changed
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( self.password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( self.password2 )

  def test_reset_password_blank( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, u"" ),
      ( self.user.object_id, u"" ),
      ( self.user2.object_id, u"" ),
      ( self.user2.object_id, u"" ),
    ) )

    assert result[ "error" ]

    # check that neither user's password has changed
    assert self.user.check_password( self.password )
    assert self.user2.check_password( self.password2 )

  def test_reset_password_multiple_users( self ):
    Stub_smtp.reset()
    smtplib.SMTP = Stub_smtp

    self.http_post( "/users/send_reset", dict(
      email_address = self.user.email_address,
      send_reset_button = u"email me",
    ) )

    matches = self.RESET_LINK_PATTERN.search( smtplib.SMTP.message )
    password_reset_id = matches.group( 2 )
    assert password_reset_id

    new_password = u"newpass"
    new_password2 = u"newpass2"
    result = self.http_post( "/users/reset_password", (
      ( u"password_reset_id", password_reset_id ),
      ( u"reset_button", u"reset passwords" ),
      ( self.user.object_id, new_password ),
      ( self.user.object_id, new_password ),
      ( self.user2.object_id, new_password2 ),
      ( self.user2.object_id, new_password2 ),
    ) )

    assert result[ u"redirect" ]

    # check that the password reset is now marked as redeemed
    password_reset = self.database.load( Password_reset, password_reset_id )
    assert password_reset.redeemed

    # check that the password was actually reset for both users
    user = self.database.load( User, self.user.object_id )
    assert user.check_password( new_password )
    user2 = self.database.load( User, self.user2.object_id )
    assert user2.check_password( new_password2 )
