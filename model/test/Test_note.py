from model.Note import Note


class Test_note( object ):
  def setUp( self ):
    self.object_id = 17
    self.title = u"title goes here"
    self.contents = u"<h3>%s</h3>blah" % self.title

    self.note = Note( self.object_id, self.contents )

  def test_create( self ):
    assert self.note.object_id == self.object_id
    assert self.note.contents == self.contents
    assert self.note.title == self.title

  def test_set_contents( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s</h3>new blah" % new_title
    previous_revision = self.note.revision

    self.note.contents = new_contents

    assert self.note.contents == new_contents
    assert self.note.title == new_title
    assert self.note.revision > previous_revision

  def test_set_contents_with_html_title( self ):
    new_title = u"new title"
    new_contents = u"<h3>%s<br/></h3>new blah" % new_title
    previous_revision = self.note.revision

    self.note.contents = new_contents

    assert self.note.contents == new_contents
    assert self.note.title == new_title
    assert self.note.revision > previous_revision

  def test_to_dict( self ):
    d = self.note.to_dict()

    assert d.get( "contents" ) == self.contents
    assert d.get( "title" ) == self.title

