import time
from controller.Html_differ import Html_differ


class Test_html_differ( object ):
  def setUp( self ):
    self.differ = Html_differ()

  def test_convert_html_to_list( self ):
    result = self.differ.convert_html_to_list( u"foo <i>bar baz</i> quux" )

    assert len( result ) == 7
    assert result[ 0 ] == u"foo "
    assert result[ 1 ] == u"<i>"
    assert result[ 2 ] == u"bar "
    assert result[ 3 ] == u"baz"
    assert result[ 4 ] == u"</i>"
    assert result[ 5 ] == u" "
    assert result[ 6 ] == u"quux"

  def test_convert_html_to_list_with_character_ref( self ):
    result = self.differ.convert_html_to_list( u"foo &#35; quux" )

    assert len( result ) == 4
    assert result[ 0 ] == u"foo "
    assert result[ 1 ] == u"&#35;"
    assert result[ 2 ] == u" "
    assert result[ 3 ] == u"quux"

  def test_convert_html_to_list_with_entity_ref( self ):
    result = self.differ.convert_html_to_list( u"foo &nbsp; quux" )

    assert len( result ) == 4
    assert result[ 0 ] == u"foo "
    assert result[ 1 ] == u"&nbsp;"
    assert result[ 2 ] == u" "
    assert result[ 3 ] == u"quux"

  def test_diff_with_insert( self ):
    a = 'foo bar baz quux'
    b = 'foo bar whee baz quux'

    result = self.differ.diff( a, b )

    assert result == 'foo bar <ins class="diff">whee </ins>baz quux'

  def test_diff_with_delete( self ):
    a = 'foo bar baz quux'
    b = 'foo bar quux'

    result = self.differ.diff( a, b )

    assert result == 'foo bar <del class="diff">baz </del>quux'

  def test_diff_with_replace( self ):
    a = 'foo bar baz quux'
    b = 'foo bar whee quux'

    result = self.differ.diff( a, b )

    assert result == 'foo bar <del class="diff modified">baz </del><ins class="diff modified">whee </ins>quux'

  def test_diff_with_italics( self ):
    a = 'foo bar baz quux'
    b = 'foo <i>bar baz</i> quux'

    result = self.differ.diff( a, b )

    assert result == 'foo <del class="diff modified">bar baz </del><ins class="diff modified"><i>bar baz</i> </ins>quux'

  def test_diff_with_italics_and_insert( self ):
    a = 'foo bar baz quux'
    b = 'foo <i>bar whee baz</i> quux'

    result = self.differ.diff( a, b )

    assert result == 'foo <del class="diff modified">bar baz </del><ins class="diff modified"><i>bar whee baz</i> </ins>quux'

  def test_diff_with_italics_twice( self ):
    a = 'foo bar baz quux <i>foo</i>'
    b = 'foo bar baz quux <i>whee</i><i>foo</i>'

    result = self.differ.diff( a, b )

    # note the screwy placement of the <ins></ins> tags. this is the best the differ can do for now
    assert result == 'foo bar baz quux <i><ins class="diff">whee</i><i></ins>foo</i>'

  def test_diff_with_link( self ):
    a = 'foo bar baz quux'
    b = 'foo bar <a href="whee">baz</a> quux'

    result = self.differ.diff( a, b )

    assert result == 'foo bar <del class="diff modified">baz </del><ins class="diff modified"><a href="whee">baz</a> </ins>quux'

  def test_diff_with_br( self ):
    a = 'foo bar baz quux'
    b = 'foo bar <br/><br />baz quux'

    result = self.differ.diff( a, b )

    assert result == 'foo bar <ins class="diff"><br /><br /></ins>baz quux'

  def test_track_open_tags( self ):
    open_tags = []

    self.differ.track_open_tags( u"foo ", open_tags )
    assert open_tags == []
    self.differ.track_open_tags( u"<br/>", open_tags )
    assert open_tags == []
    self.differ.track_open_tags( u"<i>", open_tags )
    assert open_tags == [ u"i" ]
    self.differ.track_open_tags( u"bar ", open_tags )
    assert open_tags == [ u"i" ]
    self.differ.track_open_tags( u'<a href="whee">', open_tags )
    assert open_tags == [ u"i", u"a" ]
    self.differ.track_open_tags( u"baz", open_tags )
    assert open_tags == [ u"i", u"a" ]
    self.differ.track_open_tags( u"<br />", open_tags )
    assert open_tags == [ u"i", u"a" ]
    self.differ.track_open_tags( u"</a>", open_tags )
    assert open_tags == [ u"i" ]
    self.differ.track_open_tags( u"</i>", open_tags )
    assert open_tags == []
    self.differ.track_open_tags( u"quux", open_tags )
    assert open_tags == []

  def test_prepare_lists_with_insert( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'whee ', 'baz ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # there should be no change
    assert new_a == a
    assert new_b == b

  def test_prepare_lists_with_delete( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # there should be no change
    assert new_a == a
    assert new_b == b

  def test_prepare_lists_with_replace( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'whee ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # there should be no change
    assert new_a == a
    assert new_b == b

  def test_prepare_lists_with_italics( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', '<i>', 'bar ', 'baz', '</i> ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # the elements within italics should be merged
    assert new_a == [ 'foo ', 'bar baz ', 'quux' ]
    assert new_b == [ 'foo ', '<i>bar baz</i> ', 'quux' ]

  def test_prepare_lists_with_italics_and_insert( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', '<i>', 'bar ', 'whee ', 'baz', '</i> ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # the elements within italics should be merged
    assert new_a == [ 'foo ', 'bar baz ', 'quux' ]
    assert new_b == [ 'foo ', '<i>bar whee baz</i> ', 'quux' ]

  def test_prepare_lists_with_italics_twice( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux ', '<i>', 'foo', '</i>' ]
    b = [ 'foo ', 'bar ', 'baz ', 'quux ', '<i>', 'whee', '</i>', '<i>', 'foo', '</i>' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # there should be no change, because prepare_lists() doesn't know how to merge a complex case like this
    assert new_a == a
    assert new_b == b

  def test_prepare_lists_with_link( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', '<a href="whee">', 'bar ', 'baz', '</a> ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # the elements within italics should be merged
    assert new_a == [ 'foo ', 'bar baz ', 'quux' ]
    assert new_b == [ 'foo ', '<a href="whee">bar baz</a> ', 'quux' ]

  def test_prepare_lists_with_br( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', '<br/>', '<br />', 'baz ', 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert len( result ) == 2
    ( new_a, new_b ) = result

    # there should be no change
    assert new_a == a
    assert new_b == b

  def test_prepare_lists_with_style_and_timing( self ):
    # An older version of the code took a really long time to parse certain
    # lengthy style strings due to a backtracking regular expression, so check
    # for that regression.
    start_time = time.time()
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'baz ', '<span style="' + 'a: b' * 20 + '">' , 'quux' ]

    result = self.differ.prepare_lists( a, b )

    assert time.time() - start_time < 0.5

  def test_diff_lists_with_insert( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'whee ', 'baz ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo bar <ins class="diff">whee </ins>baz quux'

  def test_diff_lists_with_delete( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo bar <del class="diff">baz </del>quux'

  def test_diff_lists_with_replace( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', 'whee ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo bar <del class="diff modified">baz </del><ins class="diff modified">whee </ins>quux'

  def test_diff_lists_with_italics( self ):
    a = [ 'foo ', 'bar baz ', 'quux' ]
    b = [ 'foo ', '<i>bar baz</i> ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo <del class="diff modified">bar baz </del><ins class="diff modified"><i>bar baz</i> </ins>quux'

  def test_diff_lists_with_italics_and_insert( self ):
    a = [ 'foo ', 'bar baz ', 'quux' ]
    b = [ 'foo ', '<i>bar whee baz</i> ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo <del class="diff modified">bar baz </del><ins class="diff modified"><i>bar whee baz</i> </ins>quux'

  def test_diff_lists_with_italics_twice( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux ', '<i>foo</i>' ]
    b = [ 'foo ', 'bar ', 'baz ', 'quux ', '<i>whee</i>', '<i>foo</i>' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo bar baz quux <ins class="diff"><i>whee</i></ins><i>foo</i>'

  def test_diff_lists_with_link( self ):
    a = [ 'foo ', 'bar baz ', 'quux' ]
    b = [ 'foo ', '<a href="whee">bar baz</a> ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo <del class="diff modified">bar baz </del><ins class="diff modified"><a href="whee">bar baz</a> </ins>quux'

  def test_diff_lists_with_br( self ):
    a = [ 'foo ', 'bar ', 'baz ', 'quux' ]
    b = [ 'foo ', 'bar ', '<br/>', '<br />', 'baz ', 'quux' ]

    result = self.differ.diff_lists( a, b )

    assert result == 'foo bar <ins class="diff"><br/><br /></ins>baz quux'
