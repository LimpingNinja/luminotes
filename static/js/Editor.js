GECKO = /Gecko/.test( navigator.userAgent ) && !/like Gecko/.test( navigator.userAgent );
WEBKIT = /WebKit/.test( navigator.userAgent );
MSIE6 = /MSIE 6\.0/.test( navigator.userAgent );
MSIE = /MSIE/.test( navigator.userAgent );
OPERA = /Opera/.test( navigator.userAgent );

FRAME_BORDER_WIDTH = 2;
FRAME_BORDER_HEIGHT = 2;


function Shared_iframe() {
  this.iframe = createDOM( "iframe",
    {
      // iframe src attribute is necessary in IE 6 on an HTTPS site to prevent annoying warnings
      "src": MSIE6 && "/static/html/blank.html" || "about:blank",
      "frameBorder": "0",
      "scrolling": "no",
      "class": "note_frame invisible",
      "height": "0"
    }
  );

  insertSiblingNodesAfter( "iframe_area", this.iframe );

  // enable design mode
  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    this.iframe.contentDocument.designMode = "On";    
  } else { // browsers such as IE
    this.iframe.contentWindow.document.designMode = "On";
  }

  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    var document = this.iframe.contentDocument;
  } else { // browsers such as IE
    var document = this.iframe.contentWindow.document;
  }

  document.open();
  var padding = '1.5em';
  if ( GECKO )
    padding = '1.5em 1.5em 1em 1.5em';
  else if ( MSIE )
    padding = '1.5em 1.5em 2.25em 1.5em';
  else if ( WEBKIT )
    padding = '0.4em 1.5em 1em 1.5em';

  document.write(
    '<html><head><style>html { padding: 0em; margin: 0; } body { padding: ' + padding + '; margin: 0; font-size: 90%; line-height: 140%; font-family: sans-serif; white-space: pre-line; word-wrap: break-word; } h3 { padding-bottom: 0.25em; border-bottom: 1px solid #dddddd; margin-bottom: 0.75em; } a[target ^= "_new"] { background: url(/static/images/web_icon_tiny.png) right center no-repeat; padding-right: 13px; } .diff a[target ^= "_new"] { background-image: none; padding-right: 0; } a:hover { color: #ff6600; } img { border-width: 0; } .left_justified { float: left; margin: 0.5em 1.5em 0.5em 0; } .center_justified { display: block; margin: 0.5em auto 0.5em auto; text-align: center; } .right_justified { float: right; margin: 0.5em 0 0.5em 1.5em; } hr { border: 0; color: #000000; background-color: #000000; height: 1px; } ul { list-style-type: disc; } ul li { margin-top: 0.5em; } ol li { margin-top: 0.5em; } .center_text { text-align: center; } .small_text { padding-top: 0.5em; font-size: 90%; } .indented { margin-left: 1em; } .thumbnail_left { float: left; margin: 0.5em; margin-right: 1em; margin-bottom: 0.5em; border: 1px solid #999999; } .thumbnail_right { float: right; margin: 0.5em; margin-left: 1em; margin-bottom: 0.5em; border: 1px solid #999999; }</style>' +
    '<meta content="text/html; charset=UTF-8" http-equiv="content-type"></meta></head><body></body></html>'
  );
  document.close();
}

Shared_iframe.prototype.editor = function () {
  return this.iframe.editor;
}


function Editor( id, notebook_id, note_text, deleted_from_id, revision, read_write, startup, highlight, focus, position_after, start_dirty, own_notes_only ) {
  this.id = id;
  this.notebook_id = notebook_id;
  this.initial_text = note_text;
  this.start_dirty = start_dirty;
  this.deleted_from_id = deleted_from_id || null;
  this.revision = revision;
  this.user_revisions = new Array(); // cache for this note's list of revisions, loaded from the server on-demand
  this.read_write = read_write;      // whether the user has read-write access to this Editor
  this.own_notes_only = own_notes_only; // whether the user only has read-write access to their own notes
  this.edit_enabled = read_write && !deleted_from_id; // whether editing is actually enabled for this Editor
  this.startup = startup || false;   // whether this Editor is for a startup note
  this.init_highlight = highlight || false;
  this.init_focus = focus || false;
  this.closed = false;
  this.link_started = null;
  this.hover_target = null;
  this.hover_timer = null;
  this.document = null;
  this.iframe = null;
  this.div = null;
  this.title = "";

  // all editors share a common design mode iframe, each claiming use of it as necessary
  if ( !Editor.shared_iframe )
    Editor.shared_iframe = new Shared_iframe();

  this.create_div( position_after );

  // if the Editor is to be focused, create an editable iframe. otherwise just create a static div
  if ( ( highlight || focus ) && this.edit_enabled )
    this.claim_iframe( position_after );
}

Editor.prototype.create_div = function ( position_after ) {
  var self = this;

  // if there is already a static note div for this Editor, connect up the note controls and bail
  var static_note_div = getElement( "static_note_" + this.id );
  if ( static_note_div ) {
    this.note_controls = getElement( "note_controls_" + this.id );
    this.holder = getElement( "note_holder_" + this.id );
    this.grabber = getElement( "note_grabber_" + this.id );
    this.connect_note_controls( true );
    this.div = static_note_div;
    this.div.editor = this;
    static_contents = getFirstElementByTagAndClassName( "span", "static_note_contents", this.div );
    if ( static_contents && static_contents.innerHTML != this.initial_text )
      static_contents.innerHTML = this.initial_text;
    this.scrape_title();
    this.focus_default_text_field();
    this.connect_handlers();
    return;
  }

  var static_contents = createDOM( "span", { "class": "static_note_contents" } );
  static_contents.innerHTML = this.contents();
  this.div = createDOM(
    "div", { "class": "static_note_div", "id": "static_note_" + this.id }, static_contents
  );
  this.div.editor = this;

  this.create_note_controls();
  this.connect_note_controls();

  this.holder = createDOM( "table", { "id": "note_holder_" + this.id, "class": "note_holder" },
    createDOM( "tbody", {},
      createDOM( "tr", {},
        createDOM( "td", {}, this.note_controls )
      ),
      createDOM( "tr", {},
        createDOM( "td", { "width": "100%" }, this.div ),
        this.grabber
      ),
      createDOM( "tr", { "id": "note_shadow_" + this.id, "class": "note_shadow undisplayed" },
        createDOM( "div", { "class": "note_shadow_corner" } )
      )
    )
  );

  if ( position_after && position_after.parentNode )
    insertSiblingNodesAfter( position_after, this.holder );
  else
    appendChildNodes( "notes", this.holder );

  this.scrape_title();
  this.focus_default_text_field();
  this.connect_handlers();

  signal( self, "init_complete" );
}

Editor.prototype.create_note_controls = function () {
  var iframe_id = "note_" + this.id;

  this.grabber = createDOM( "td", { "id": "note_grabber_" + this.id, "class": "note_grabber" }, "....." );
  if ( !this.read_write || this.own_notes_only )
    addElementClass( this.grabber, "invisible" );

  if ( this.read_write ) {
    this.delete_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "delete_" + iframe_id,
      "value": "delete" + ( this.deleted_from_id ? " forever" : "" ),
      "title": "delete note [ctrl-d]"
    } );

    if ( this.deleted_from_id ) {
      this.undelete_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "undelete_" + iframe_id,
        "value": "undelete",
        "title": "undelete note"
      } );
    } else if ( !this.own_notes_only ) {
      this.changes_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "changes_" + iframe_id,
        "value": "changes",
        "title": "previous revisions"
      } );

      this.tools_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "tools_" + iframe_id,
        "value": "tools",
        "title": "note tools"
      } );
    }
  }

  if ( !this.deleted_from_id && ( this.read_write || !this.startup ) && !this.own_notes_only ) {
    this.hide_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "hide_" + iframe_id,
      "value": "hide",
      "title": "hide note [ctrl-h]"
    } );
  }

  this.note_controls = createDOM(
    "div", { "class": "note_controls", "id": "note_controls_" + this.id },
    this.delete_button ? this.delete_button : null,
    this.delete_button ? " " : null,
    this.changes_button ? this.changes_button : null,
    this.changes_button ? " " : null,
    this.tools_button ? this.tools_button : null,
    this.tools_button ? " " : null,
    this.undelete_button ? this.undelete_button : null,
    this.undelete_button ? " " : null,
    this.hide_button ? this.hide_button : null
  );
}

Editor.prototype.connect_note_controls = function ( store_control_buttons ) {
  if ( store_control_buttons ) {
    var iframe_id = "note_" + this.id;
    this.delete_button = getElement( "delete_" + iframe_id );
    this.undelete_button = getElement( "undelete_" + iframe_id );
    this.changes_button = getElement( "changes_" + iframe_id );
    this.tools_button = getElement( "tools_" + iframe_id );
    this.hide_button = getElement( "hide_" + iframe_id );
  }

  var self = this;
  if ( this.delete_button ) {
    disconnectAll( this.delete_button );
    connect( this.delete_button, "onclick", function ( event ) { signal( self, "delete_clicked", event ); } );
  }
  if ( this.undelete_button ) {
    disconnectAll( this.undelete_button );
    connect( this.undelete_button, "onclick", function ( event ) { signal( self, "undelete_clicked", event ); } );
  }
  if ( this.changes_button ) {
    disconnectAll( this.changes_button );
    connect( this.changes_button, "onclick", function ( event ) { signal( self, "changes_clicked", event ); } );
  }
  if ( this.tools_button ) {
    disconnectAll( this.tools_button );
    connect( this.tools_button, "onclick", function ( event ) { signal( self, "tools_clicked", event ); } );
  }
  if ( this.hide_button ) {
    disconnectAll( this.hide_button );
    connect( this.hide_button, "onclick", function ( event ) { signal( self, "hide_clicked", event ); } );
  }

  if ( this.grabber ) {
    disconnectAll( this.grabber );
    connect( this.grabber, "onmousedown", function ( event ) { self.start_drag( event ); } );
    connect( this.grabber, "onclick", function ( event ) { event.stop(); } );
  }
}

Editor.prototype.claim_iframe = function ( position_after ) {
  var self = this;
  var iframe_id = "note_" + this.id;

  // if there is already an iframe for this Editor, bail
  if ( this.iframe )
    return;

  // claim the reusable iframe for this note, stealing it from the note that's using it (if any)
  this.iframe = Editor.shared_iframe.iframe;
  this.iframe.setAttribute( "id", iframe_id );
  this.iframe.setAttribute( "name", iframe_id );

  if ( this.iframe.editor )
    this.iframe.editor.release_iframe();
  this.iframe.editor = this;

  // setup the note controls
  this.note_controls = getElement( "note_controls_" + this.id );
  this.connect_note_controls( true );

  // give the iframe the note's current contents and then resize it based on the size of the div
  var range = this.add_selection_bookmark();
  this.set_iframe_contents( this.contents() );
  this.remove_selection_bookmark( range );
  this.resize( true );

  // make the completed iframe visible and hide the static div
  addElementClass( this.iframe, "focused_note_frame" );
  removeElementClass( this.iframe, "invisible" );
  addElementClass( this.div, "invisible" );
  addElementClass( this.grabber, "note_grabber_focused" );

  function finish_init() {
    self.position_cursor( range );
    self.connect_handlers();
    signal( self, "focused", self );
    self.focus( true );
  }

  // this small delay gives Firefox enough lag time after set_iframe_contents() to display the
  // blinking text cursor at the end of the iframe contents
  if ( GECKO && !range )
    setTimeout( finish_init, 1 );
  else
    finish_init();
}

Editor.prototype.set_iframe_contents = function ( contents_text ) {
  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    this.document = this.iframe.contentDocument;
  } else { // browsers such as IE
    this.document = this.iframe.contentWindow.document;
  }

  // hack: add a zero-width space to make the horizontal line under title show up in the
  // correct position, even before there is a title
  if ( !contents_text )
    contents_text = "<h3>&#8203;";

  this.document.body.innerHTML = contents_text;
}

Editor.prototype.focus_default_text_field = function () {
  // special-case: focus any username field found within this div
  var username = getElement( "username" );
  if ( username && isChildNode( username, this.div ) )
    username.focus();
}

Editor.prototype.add_selection_bookmark = function () {
  if ( window.getSelection ) { // browsers such as Firefox
    // grab the current range for this editor's div so that it can be duplicated within the iframe
    var selection =  window.getSelection();
    if ( selection.rangeCount > 0 )
      var range = selection.getRangeAt( 0 );
    else
      var range = document.createRange();

    // if the current range is not within this editor's static note div, then bail
    if ( range.startContainer == document || range.endContainer == document )
      return null;
    try {
      if ( !isChildNode( range.startContainer.parentNode, this.div ) || !isChildNode( range.endContainer.parentNode, this.div ) )
        return null;
    } catch ( e ) {
      return null;
    }

    // mark the nodes that are start and end containers for the current range. we have to mark the
    // parent node instead of the start/end container itself, because text nodes can't have classes
    var parent_node = range.startContainer.parentNode
    if ( !hasElementClass( parent_node, "static_note_div" ) ) {
      addElementClass( parent_node, "range_start_container" );
      for ( var i in parent_node.childNodes ) {
        var child_node = parent_node.childNodes[ i ];
        if ( child_node == range.startContainer ) {
          range.start_child_offset = i;
          break;
        }
      }
    }

    var parent_node = range.endContainer.parentNode
    if ( !hasElementClass( parent_node, "static_note_div" ) ) {
      addElementClass( parent_node, "range_end_container" );
      for ( var i in parent_node.childNodes ) {
        var child_node = parent_node.childNodes[ i ];
        if ( child_node == range.endContainer ) {
          range.end_child_offset = i;
          break;
        }
      }
    }

    return range;
  } else if ( document.selection ) { // browsers such as IE
    var range = document.selection.createRange();
    if ( !isChildNode( range.parentElement(), this.div ) )
      return null;

    return range;
  }

  return null;
}

Editor.prototype.remove_selection_bookmark = function ( range ) {
  // unmark the nodes that are start and end containers for the given range
  if ( range && range.startContainer && range.endContainer ) {
    removeElementClass( range.startContainer.parentNode, "range_start_container" );
    removeElementClass( range.endContainer.parentNode, "range_end_container" );
  }
}

Editor.prototype.position_cursor = function ( div_range ) {
  if ( this.init_focus ) {
    this.init_focus = false;
    if ( this.iframe )
      this.focus( true );
  }

  // if requested, move the text cursor to a specific location
  if ( div_range && this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    // position the cursor by using a bookmarked text range
    var selection = this.iframe.contentWindow.getSelection();

    selection.removeAllRanges();
    var range = this.document.createRange();

    var start = getFirstElementByTagAndClassName( null, "range_start_container", this.document );
    var end = getFirstElementByTagAndClassName( null, "range_end_container", this.document );

    // if start and end don't exist, assume that they are the top-level document body node. this
    // occurs when start and end are set to the div's static_note_contents node, which doesn't exist
    // within the iframe
    if ( !start && !end ) {
      start = this.document.body;
      end = this.document.body;
    }

    if ( start && end ) {
      removeElementClass( start, "range_start_container" );
      removeElementClass( end, "range_end_container" );
      if ( div_range.start_child_offset )
        start = start.childNodes[ div_range.start_child_offset ];
      if ( div_range.end_child_offset )
        end = end.childNodes[ div_range.end_child_offset ];
      range.setStart( start, div_range.startOffset );
      range.setEnd( end, div_range.endOffset );
      selection.addRange( range );
      return;
    }
  } else if ( div_range && this.document && this.document.selection ) { // browsers such as IE
    function text_length( text ) {
      var count = 0;
      for ( var i = 0; i < text.length; i++ ) {
        if ( text.charAt( i ) != "\r" )
          count++;
      }
      return count;
    }

    // create a range that extends from the start of the div to the start of the original range
    var before_div_range = div_range.duplicate();
    before_div_range.moveToElementText( this.div );
    before_div_range.setEndPoint( "EndToStart", div_range );

    // calculate the start offset based on the size of that range in characters
    var start = text_length( before_div_range.text ) - 1;
    var end = start + text_length( div_range.text );

    // finally, position the text cursor within the iframe
    var range = this.document.selection.createRange();
    range.moveEnd( "character", end );
    range.moveStart( "character", start );
    range.select();

    return;
  }

  // otherwise, just move the text cursor to the end of the text
  if ( this.iframe && this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    var last_node = this.document.body.lastChild;

    selection.removeAllRanges();
    var range = this.document.createRange();

    while ( ( last_node.nodeValue == "\n" || ( last_node.tagName && last_node.tagName == "BR" ) ) &&
            last_node.previousSibling )
      last_node = last_node.previousSibling;

    range.selectNodeContents( last_node );
    range.collapse( false );
    selection.addRange( range );
  } else if ( this.document && this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    range.move( "textedit" );
    range.select();
  }
}

Editor.prototype.position_cursor_after = function ( node ) {
  if ( this.iframe && this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    selection.selectAllChildren( node );
    selection.collapseToEnd();
  }
}

Editor.prototype.collapse_cursor = function () {
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    if ( !selection.isCollapsed )
      selection.collapseToEnd();
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    range.collapse( false );
    range.select();
  }
}

Editor.prototype.connect_handlers = function () {
  if ( this.document && this.document.body ) {
    // since the browser may subtly tweak the html when it's inserted, save off the browser's version
    // of the html here. this yields more accurate comparisons within the dirty() method
    if ( this.start_dirty )
      this.initial_text = "";
    else
      this.initial_text = this.document.body.innerHTML;
  }

  var self = this; // necessary so that the member functions of this editor object are used

  if ( !this.iframe ) {
    connect( this.div, "onmouseup", function ( event ) { self.mouse_released( event ); } );
    connect( this.div, "onclick", function ( event ) { self.mouse_clicked( event ) } );
    connect( this.div, "onmouseover", function ( event ) { self.mouse_hovered( event ); } );
    connect( this.div, "ondragover", function ( event ) { self.mouse_dragged( event ); } );
  } else {
    if ( this.edit_enabled ) {
      connect( this.document, "onkeydown", function ( event ) { self.key_pressed( event ); } );
      connect( this.document, "onkeyup", function ( event ) { self.key_released( event ); } );
    }
    connect( this.document, "onmouseup", function ( event ) { self.mouse_released( event ); } );
    connect( this.document, "onclick", function ( event ) { self.mouse_clicked( event ); } );
    connect( this.document, "onmouseover", function ( event ) { self.mouse_hovered( event ); } );
    connect( this.document, "ondragover", function ( event ) { self.mouse_dragged( event ); } );
    connect( this.iframe, "onload", function () { self.resize(); } );
    connect( this.iframe, "onresize", function () { setTimeout( function () { self.resize() }, 50 ); } );
    connect( this.iframe.contentWindow, "onpaste", function ( event ) { setTimeout( function () { self.resize() }, 50 ); } );
    connect( this.iframe.contentWindow, "oncut", function ( event ) { setTimeout( function () { self.resize() }, 50 ); } );
  }

  // handle each form submit event by forwarding it on as a custom event
  function connect_form( form ) {
    disconnectAll( form );
    connect( form, "onsubmit", function ( event ) {
      signal( self, "submit_form", form );
      event.stop();
    } );
  }

  var forms = getElementsByTagAndClassName( "form", null, this.div );
  for ( var i in forms ) {
    var form = forms[ i ];
    connect_form( form );
  }

  // connect each (non-submit) button to issue an event
  function connect_button( button ) {
    disconnectAll( button );
    connect( button, "onclick", function ( event ) {
      signal( self, "button_clicked", this, button );
      event.stop();
    } );
  }

  var buttons = getElementsByTagAndClassName( "input", "button", this.div );
  for ( var i in buttons ) {
    var button = buttons[ i ];
    if ( button.getAttribute( "type" ) == "submit" )
      continue;

    connect_button( button );
  }

  // browsers such as Firefox, but not Opera
  if ( GECKO && this.iframe && this.iframe.contentDocument && this.edit_enabled ) {
    this.exec_command( "styleWithCSS", false );
    this.exec_command( "insertbronreturn", true );
  }

  if ( this.init_highlight ) {
    this.highlight();
    this.init_highlight = false;
  }

  this.scrape_title();

  signal( self, "init_complete" );
}

Editor.prototype.highlight = function ( scroll ) {
  if ( scroll == undefined )
    scroll = true;

  var self = this;

  function do_highlight() {
    if ( !self.iframe ) {
      new Highlight( self.div, options = { "queue": { "scope": "highlight", "limit": 1 } } );
      return;
    }

    if ( OPERA ) { // MochiKit's Highlight for iframes is broken in Opera
      pulsate( self.iframe, options = { "pulses": 1, "duration": 0.5 } );
    } else if ( self.iframe.contentDocument ) { // browsers such as Firefox
      new Highlight( self.iframe, options = { "queue": { "scope": "highlight", "limit": 1 } } );
    } else { // browsers such as IE
      if ( self.document && self.document.body )
        new Highlight( self.document.body, options = { "queue": { "scope": "highlight", "limit": 1 } } );
    }
  }

  // focusing the highlighted editor before scrolling to it prevents IE from deciding to
  // automatically scroll back to the link immediately afterwards
  this.focus();

  if ( scroll ) {
    var editor_node = this.iframe || this.div;

    // if the editor is already completely on-screen, then there's no need to scroll
    var viewport_position = getViewportPosition();
    if ( getElementPosition( this.note_controls ).y < viewport_position.y ||
         getElementPosition( editor_node ).y + getElementDimensions( editor_node ).h > viewport_position.y + getViewportDimensions().h ) {
      new ScrollTo( this.note_controls, { "afterFinish": do_highlight, "duration": 0.25 } );
      return;
    }
  }

  do_highlight();
}

Editor.prototype.exec_command = function ( command, parameter ) {
  command = command.toLowerCase();

  if ( command == "h3" ) {
    if ( this.state_enabled( "h3" ) )
      this.document.execCommand( "formatblock", false, "<p>" );
    else
      this.document.execCommand( "formatblock", false, "<h3>" );
    return;
  }

  this.document.execCommand( command, false, parameter );
}

Editor.prototype.insert_html = function ( html ) {
  if ( html.length == 0 ) return;

  if ( !this.edit_enabled || strip( this.contents() ) == "" ) {
    this.document.body.innerHTML = html;
    return;
  }

  try { // browsers supporting insertHTML command, such as Firefox
    this.document.execCommand( "insertHTML", false, html );
  } catch ( e ) { // browsers that don't support insertHTML, such as IE
    this.document.body.innerHTML = html;
  }
}

Editor.prototype.query_command_value = function ( command ) {
  return this.document.queryCommandValue( command );
}

// resize the editor's frame to fit the dimensions of its content
Editor.prototype.resize = function ( get_height_from_div ) {
  if ( !this.document ) return;

  this.reposition();

  var height = null;
  var width = elementDimensions( this.div ).w;

  // set the width first, because that influences the height of the content
  width -= FRAME_BORDER_HEIGHT * 2;
  var size = { "w": width };
  setElementDimensions( this.iframe, size );

  if ( get_height_from_div && !this.empty() ) {
    height = elementDimensions( this.div ).h;
    height -= FRAME_BORDER_HEIGHT * 2; // 2 pixels at the top and 2 at the bottom
  // if no height is given, get the height from this editor's document body
  } else {
    if ( this.iframe && this.iframe.contentDocument && GECKO ) { // Gecko and other sane browsers
      height = elementDimensions( this.document.documentElement ).h;
    } else { // IE
      height = this.document.body.scrollHeight;
    }
  }

  size = { "h": height };
  setElementDimensions( this.iframe, size );
  setElementDimensions( this.div, size );

  var self = this;
}

Editor.prototype.reposition = function ( repeat ) {
  if ( !this.iframe ) return;

  // give the iframe the exact same position as the div it replaces. subtract the position of the
  // center_content_area container, which is relatively positioned
  var position = getElementPosition( this.div );
  var orig_position = getElementPosition( this.iframe );
  if ( repeat && position.x == orig_position.x && position.y == orig_position.y )
    return;

  var container_position = getElementPosition( "center_content_area" );
  position.x -= container_position.x;
  position.y -= container_position.y;

  setElementPosition( this.iframe, position );

  var self = this;
  setTimeout( function () { self.reposition( true ); }, 50 );
}

Editor.prototype.start_drag = function ( event ) {
  event.stop();

  var note_height = 100;
  mouse_position = event.mouse().page;

  addElementClass( this.div, "note_div_dragging" );

  // add a blank div to the area where the editor is popping out from. this lets the user easily
  // see where the editor came from
  var drop_target = createDOM( "div", { "class": "note_drag_source_area", "id": "note_drag_source_area" } );
  insertSiblingNodesAfter( this.holder, drop_target );
  var div_size = getElementDimensions( this.div );
  div_size.w -= FRAME_BORDER_WIDTH * 2;
  setElementDimensions( drop_target, div_size );

  // add drop target divs between every note and before the first note
  var holders = getElementsByTagAndClassName( "table", "note_holder" );
  if ( holders[ 0 ] != this.holder ) {
    drop_target = createDOM( "div", { "class": "note_drop_target" } );
    insertSiblingNodesBefore( holders[ 0 ], drop_target );
    setElementDimensions( drop_target, { "w": div_size.w } );
  }

  for ( var i in holders ) {
    var holder = holders[ i ];
    i = parseInt( i );
    var next_holder = ( i + 1 < holders.length ) && holders[ i + 1 ] || null;

    if ( holder == this.holder || next_holder == this.holder ) continue;

    drop_target = createDOM( "div", { "class": "note_drop_target" } );
    insertSiblingNodesAfter( holder, drop_target );
    setElementDimensions( drop_target, { "w": div_size.w } );
  }

  // vertically reposition the editor so that at least some part of it is under the mouse cursor
  var viewport_position = getViewportPosition();
  var position = getElementPosition( this.div );

  var new_position = null;
  setElementDimensions( this.holder, { "w": getElementDimensions( this.holder ).w } );

  // if the click position is above the editor, then move the top of the editor up to it
  if ( mouse_position.y < position.y )
    new_position = { "y": mouse_position.y };
  // if the click position is below the editor, then move the bottom of the editor down to it
  else if ( mouse_position.y > position.y + note_height )
    new_position = { "y": mouse_position.y - note_height };
  else
    new_position = { "y": getElementPosition( this.holder ).y };

  // save the offset of the mouse click from the top-left of the holder
  this.drag_click_offset = {
    "x": mouse_position.x - getElementPosition( this.holder ).x,
    "y": mouse_position.y - new_position.y
  };

  new_position.y -= viewport_position.y;
  setElementPosition( this.holder, new_position );

  addElementClass( this.holder, "note_holder_dragging" );
  addElementClass( this.note_controls, "invisible" );
  addElementClass( this.grabber, "note_grabber_focused" );
  removeElementClass( getElement( "note_shadow_" + this.id ), "undisplayed" );
  signal( this, "grabber_pressed", event );

  var self = this;
  this.drag_signal = connect( window.document.body, "onmousemove", function ( event ) { self.drag( event ); } );
  this.drop_signal = connect( window.document.body, "onmouseup", function ( event ) { self.drop( event ); } );
}

Editor.prototype.drag = function( event ) {
  event.stop();

  if ( this.drag_target_timer )
    clearTimeout( this.drag_target_timer );

  var mouse_position = event.mouse().page;

  // move the editor based on the original click's offset
  var viewport_position = getViewportPosition();
  setElementPosition( this.holder, {
    "x": mouse_position.x - this.drag_click_offset.x - viewport_position.x,
    "y": mouse_position.y - this.drag_click_offset.y - viewport_position.y
  } );

  var self = this;

  function hover_drag_targets() {
    // if the editor is over any drop targets, expand and color them accordingly
    var drop_targets = getElementsByTagAndClassName( "div", "note_drop_target" );
    var div_position = getElementPosition( self.div );
    var div_size = getElementDimensions( self.div );

    for ( var i in drop_targets ) {
      var drop_target = drop_targets[ i ];
      var target_position = getElementPosition( drop_target );
      var target_size = getElementDimensions( drop_target );
      if ( WEBKIT ) {
        target_position.x -= viewport_position.x;
        target_position.y -= viewport_position.y;
      }

      // if the div is wholly above or below the drop target, then it's not overlapping it
      if ( ( div_position.y < target_position.y && div_position.y + div_size.h < target_position.y ) ||
           ( div_position.y > target_position.y + target_size.h && div_position.y + div_size.h > target_position.y + target_size.h ) )
        removeElementClass( drop_target, "note_drop_target_hover" );
      else
        addElementClass( drop_target, "note_drop_target_hover" );
    }
  }

  // testing drag targets for hovering can be slow, so only do it periodically (a split second after the mouse stops moving)
  this.drag_target_timer = setTimeout( function () { hover_drag_targets(); }, 10 );

  this.drag_scroll( event.mouse().client );
}

Editor.prototype.drag_scroll = function( mouse_viewport_position ) {
  if ( this.drag_scroll_timer )
    clearTimeout( this.drag_scroll_timer );

  // if the mouse is near the top or the bottom of the viewport, scroll the page accordingly. this
  // allows the user to reach other notes while dragging a note
  var viewport_size = getViewportDimensions();
  var scroll_height = 0;
  var SCROLL_TRIGGER_AREA_HEIGHT = 50;
  var SCROLL_RATE = 40;

  if ( mouse_viewport_position.y > viewport_size.h - SCROLL_TRIGGER_AREA_HEIGHT )
    scroll_height = SCROLL_RATE;
  else if ( mouse_viewport_position.y < SCROLL_TRIGGER_AREA_HEIGHT )
    scroll_height = -SCROLL_RATE;
  else {
    return;
  }

  var page_top = document.body.scrollTop || window.pageYOffset;
  window.scrollBy( 0, scroll_height );
  var new_page_top = document.body.scrollTop || window.pageYOffset;

  // if scrolling didn't work, then we're at the top or the bottom of the page, so bail
  if ( page_top == new_page_top )
    return;

  var self = this;
  this.drag_scroll_timer = setTimeout( function () { self.drag_scroll( mouse_viewport_position ); }, 50 );
}

Editor.prototype.drop = function( event ) {
  disconnect( this.drag_signal );
  disconnect( this.drop_signal );
  if ( this.drag_scroll_timer )
    clearTimeout( this.drag_scroll_timer );
  if ( this.drag_target_timer )
    clearTimeout( this.drag_target_timer );

  removeElementClass( this.div, "note_div_dragging" );
  removeElementClass( this.holder, "note_holder_dragging" );
  removeElementClass( this.note_controls, "invisible" );
  removeElementClass( this.grabber, "note_grabber_focused" );
  addElementClass( getElement( "note_shadow_" + this.id ), "undisplayed" );

  this.drag_mouse_position = null;

  // if there is a hovered drop target, move the editor to it
  var hover_drop_target = getFirstElementByTagAndClassName( "div", "note_drop_target_hover" );
  if ( hover_drop_target ) {
    setElementPosition( this.holder, getElementPosition( hover_drop_target ) );
    swapDOM( hover_drop_target, this.holder );
    removeElement( "note_drag_source_area" );
    this.resize();
    this.highlight();
    signal( this, "moved", this, this.previous_editor(), this.next_editor() );
  }

  var drop_targets = getElementsByTagAndClassName( "div", "note_drop_target" );
  for ( var i in drop_targets )
    removeElement( drop_targets[ i ] );

  // if there is no hovered drop target, just move the editor back to its original location
  if ( !hover_drop_target ) {
    var drag_source_area = getElement( "note_drag_source_area" );
    setElementPosition( this.holder, getElementPosition( drag_source_area ) );
    removeElement( drag_source_area );
    this.resize();
    this.highlight();
  }
}

Editor.prototype.previous_editor = function () {
  var previous_holder = this.holder.previousSibling;
  while ( previous_holder && previous_holder.nodeValue == "\n" )
    previous_holder = previous_holder.previousSibling;
  if ( !previous_holder || !hasElementClass( previous_holder, "note_holder" ) ) return null;
  var div = getFirstElementByTagAndClassName( "div", "static_note_div", previous_holder );
  if ( !div || !div.editor ) return null;

  return div.editor;
}

Editor.prototype.next_editor = function () {
  var next_holder = this.holder.nextSibling;
  while ( next_holder && next_holder.nodeValue == "\n" )
    next_holder = next_holder.nextSibling;
  if ( !next_holder || !hasElementClass( next_holder, "note_holder" ) ) return null;
  var div = getFirstElementByTagAndClassName( "div", "static_note_div", next_holder );
  if ( !div || !div.editor ) return null;

  return div.editor;
}

Editor.prototype.key_pressed = function ( event ) {
  signal( this, "key_pressed", this, event );

  this.resize();
}

Editor.prototype.key_released = function ( event ) {
  this.resize();

  // if ctrl keys are released, bail
  var code = event.key().code;
  var CTRL = 17;
  var NONE = 0;

  if ( event.modifier().ctrl || code == CTRL || code == NONE )
    return;

  this.cleanup_html( code );

  signal( this, "state_changed", this, false );
}

Editor.prototype.cleanup_html = function ( key_code ) {
  if ( WEBKIT ) {
    // if enter is pressed while in a title, end title mode, since WebKit doesn't do that for us
    var ENTER = 13; BACKSPACE = 8;
    if ( key_code == ENTER && this.state_enabled( "h3" ) )
      this.exec_command( "h3" );

    // if backspace is pressed, skip WebKit style scrubbing since it can cause problems
    if ( key_code == BACKSPACE )
      return null;

    // as of this writing, WebKit doesn't support execCommand( "styleWithCSS" ). for more info, see
    // https://bugs.webkit.org/show_bug.cgi?id=13490
    // so to make up for this shortcoming, manually scrub WebKit style spans and other nodes,
    // replacing them with appropriate tags
    var style_spans = getElementsByTagAndClassName( "span", null, this.document );
    var underlines = getElementsByTagAndClassName( "u", null, this.document );
    var strikethroughs = getElementsByTagAndClassName( "strike", null, this.document );
    var fonts = getElementsByTagAndClassName( "font", "Apple-style-span", this.document );
    var nodes = style_spans.concat( underlines ).concat( strikethroughs ).concat( fonts );

    for ( var i in nodes ) {
      var node = nodes[ i ];
      if ( !node ) continue;

      var style = node.getAttribute( "style" );

      node.removeAttribute( "class" );
      if ( style == undefined && node.tagName != "font" && node.tagName != "FONT" )
        continue;
      if ( getStyle( node, "color" ) || getStyle( node, "background-color" ) )
        continue;

      var replacement = withDocument( this.document, function () {
        // font-size is set when ending title mode
        if ( style.indexOf( "font-size: " ) != -1 )
          return null;
        if ( style.indexOf( "text-decoration: none;" ) != -1 || style.length == 0 )
          return createDOM( "span" );
        if ( style.indexOf( "font-weight: bold;" ) != -1 )
          return createDOM( "b" );
        if ( style.indexOf( "font-style: italic;" ) != -1 )
          return createDOM( "i" );
        if ( style.indexOf( "text-decoration: underline;" ) != -1 )
          return createDOM( "u" );
        if ( style.indexOf( "text-decoration: line-through;" ) != -1 )
          return createDOM( "strike" );
        return null;
      } );

      if ( replacement ) {
        var selection = this.iframe.contentWindow.getSelection();
        var anchor = selection.anchorNode;
        var offset = selection.anchorOffset;
        swapDOM( node, replacement );
        appendChildNodes( replacement, node.childNodes );

        // necessary to prevent the text cursor from disappearing as the node containing it is replaced
        selection.collapse( anchor, offset );
      } else {
        node.removeAttribute( "style" );
      }
    }
  }

  // the rest only applies to Firefox and other Gecko-based browsers
  if ( !GECKO )
    return;

  // if you're typing the text of an <h3> title and you hit enter, the text cursor will skip a line
  // and then move back up a line when you start typing again. to prevent this behavior, remove an
  // extra <br> tag when this situation is detected before the current node: <h3><br>
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) {
    var selection = this.iframe.contentWindow.getSelection();
    var range = selection.getRangeAt( 0 );
    var startOffset = range.startOffset;

    var node = range.startContainer.childNodes[ startOffset ];
    if ( node && node.previousSibling && node.previousSibling.previousSibling &&
         node.previousSibling.nodeName == "BR" &&
         node.previousSibling.previousSibling.nodeName == "H3" ) {
      removeElement( node.previousSibling );
      if ( node.nodeName != "BR" )
        insertSiblingNodesBefore( node, createDOM( "br" ) );
      else
        this.resize();
    }
  }
}

Editor.prototype.cleanup_range = function () {
  if ( this.iframe && this.iframe.contentWindow.getSelection ) {
    var selection =  this.iframe.contentWindow.getSelection();
    if ( selection.isCollapsed )
      this.exec_command( "removeformat" );
  }
}

Editor.prototype.unformat_selection = function () {
  if ( !this.iframe || !this.document )
    return false;

  // if the selection is collapsed, then there is nothing to unformat
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    var range = selection.getRangeAt( 0 );
    if ( range.collapsed )
      return false;
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    var collapsed_range = range.duplicate();
    collapsed_range.collapse();
    if ( range.isEqual( collapsed_range ) )
      return false;
  }

  // first, remove all standard formatting (<b>, <i>, etc.)
  this.exec_command( "removeformat" );

  // then, remove all other "formatting" that removeformat doesn't touch (<h1>, <h2>, etc.)
  var nodes =
    getElementsByTagAndClassName( "h1", null, this.document ).concat(
    getElementsByTagAndClassName( "h2", null, this.document ) ).concat(
    getElementsByTagAndClassName( "h3", null, this.document ) ).concat(
    getElementsByTagAndClassName( "h4", null, this.document ) ).concat(
    getElementsByTagAndClassName( "h5", null, this.document ) ).concat(
    getElementsByTagAndClassName( "h6", null, this.document ) );

  for ( var i in nodes ) {
    var node = nodes[ i ];
    if ( !node ) continue;

    // before proceeding, make sure the node is within the selected text
    if ( selection && selection.containsNode ) { // browsers such as Firefox
      if ( !selection.containsNode( node, true ) )
        continue;
    } else if ( this.document.selection ) {
      var node_range = this.document.selection.createRange();
      node_range.moveToElementText( node );
      if ( !range.inRange( node_range ) )
        continue;
    }

    var replacement = withDocument( this.document, function () { return createDOM( "span" ); } );
    swapDOM( node, replacement );
    appendChildNodes( replacement, node.childNodes );
  }

  return true;
}

Editor.prototype.mouse_released = function ( event ) {
  this.link_started = null;
  var self = this;

  function handle_click( event ) {
    // we only want to deal with left mouse button clicks
    if ( event.mouse().button.right )
      return false;

    // search through the tree of elements containing the clicked target. if a link isn't found, bail
    var link = event.target()
    if ( !link ) false;

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link )
        return false;
    }
    if ( !link.href ) return false;

    var query = parse_query( link );
    var id = query.note_id;

    // special case for links to uploaded files
    if ( !link.target && /\/files\//.test( link.href ) ) {
      if ( !/\/files\/new$/.test( link.href ) ) {
        window.open( link.href );
      }
      return true;
    }

    // middle click opens the link in a new window
    if ( event.mouse().button.middle ) {
      window.open( link.href );
      return true;
    }

    // links with targets are considered to be external links pointing outside of this wiki
    if ( link.target || id == undefined ) {
      // if this is a read-only editor and the link target is "_top", go to the link's URL directly
      if ( !self.edit_enabled && ( link.target == "_top" || !link.target ) ) {
        window.location = link.href;
        return true;
      }
      
      // launch the external link ourselves, assuming that its target is "_new"
      window.open( link.href );
      if ( !link.target )
        link.target = "_top";
      return true;
    }

    // load the note corresponding to the clicked link
    var title = link_title( link, query );
    signal( self, "load_editor", title, id, null, null, link, self.holder );
    return true;
  }

  var link_clicked = handle_click( event );

  if ( this.edit_enabled ) {
    // if no link was clicked, then make the clicked editor into an iframe
    if ( !link_clicked && this.div ) {
      this.init_focus = true;

      this.claim_iframe( null );
    }

    // in case the cursor has moved, update the state
    signal( this, "state_changed", this, link_clicked );
  }
}

Editor.prototype.mouse_clicked = function ( event ) {
  if ( event.mouse().button.middle || event.mouse().button.right )
    return;

  var target = event.target();
  if ( !target ) return;

  var tag_name = target.tagName;
  if ( !tag_name ) return;
  tag_name = tag_name.toLowerCase();

  // allow clicks on buttons, labels, and input fields
  if ( tag_name == "button" || tag_name == "label" || tag_name == "input" )
    return;

  // block all other clicks (e.g. on links, to prevent the browser from handling link clicks itself)
  event.stop();
}

HOVER_DURATION_MILLISECONDS = 1000;

Editor.prototype.mouse_hovered = function ( event ) {
  // ignore mouse hover events for static div notes
  if ( !this.iframe )
    return;

  // search through the tree of elements containing the hover target for a link
  var link = event.target()
  if ( !link ) false;

  while ( link.nodeName != "A" ) {
    link = link.parentNode;
    if ( !link )
      break;
  }
  if ( !link || !link.href )
    link = null;

  var self = this;
  var hover_target = link || event.target();
  this.hover_target = hover_target;

  if ( this.hover_timer )
    clearTimeout( this.hover_timer );

  this.hover_timer = setTimeout( function () { self.mouse_hover_timeout( hover_target ) }, HOVER_DURATION_MILLISECONDS );
}

Editor.prototype.mouse_hover_timeout = function ( hover_target ) {
  // if the mouse is hovering over the same target that it was when the timer started
  if ( hover_target == this.hover_target && this.iframe )
    signal( this, "mouse_hovered", hover_target );
}

Editor.prototype.mouse_dragged = function ( event ) {
  // reset the hover timer to prevent a mouse hover from being registered while the mouse is being dragged
  if ( this.hover_timer ) {
    var self = this;
    clearTimeout( this.hover_timer );
    this.hover_timer = setTimeout( function () { self.mouse_hover_timeout( self.hover_target ) }, HOVER_DURATION_MILLISECONDS );
  }
}

Editor.prototype.scrape_title = function () {
  // scrape the note title out of the editor
  var heading = getFirstElementByTagAndClassName( "h3", null, this.document || this.div );
  if ( heading )
    var title = scrapeText( heading );
  else
    var title = "";

  // issue a signal that the title has changed and save off the new title
  if ( this.edit_enabled )
    signal( this, "title_changed", this, this.title, title );
  this.title = title;
}

Editor.title_placeholder_char = "\u200b";
Editor.title_placeholder_pattern = /\u200b/g;
Editor.title_placeholder_html = "&#8203;&#8203;";

Editor.prototype.empty = function () {
  if ( this.iframe && this.document && this.document.body )
    var node = this.document.body;
  else if ( this.div )
    var node = this.div;
  else
    return true;

  return ( scrapeText( node ).replace( Editor.title_placeholder_pattern, "" ).length == 0 );
}

Editor.prototype.insert_link = function ( url ) {
  // get the current selection, which is the link title
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();

    // if no text is selected, then insert a link with two zero-width spaces as the title. then,
    // position the text cursor between the two zero-width spaces. yes, this really is necessary.
    // it ensures that the next character typed in WebKit becomes part of the link title.
    if ( selection.toString().length == 0 ) {
      this.insert_html( '<a href="' + url + '" id="new_link">' + Editor.title_placeholder_html + '</a>' );
      var link = withDocument( this.document, function () { return getElement( "new_link" ); } );
      link.removeAttribute( "id" );
      selection.selectAllChildren( link );
      selection.collapse( link.firstChild, 1 );
      this.link_started = link;
    // otherwise, just create a link with the selected text as the link title
    } else {
      this.link_started = null;
      this.exec_command( "createLink", url );
      return this.find_link_at_cursor();
    }
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();

    // if no text is selected, then insert a link with a placeholder space as the link title, and
    // then select it
    if ( range.text.length == 0 ) {
      range.text = " ";
      range.moveStart( "character", -1 );
      range.select();
      this.exec_command( "createLink", url );
      this.link_started = this.find_link_at_cursor();
    } else {
      this.link_started = null;
      this.exec_command( "createLink", url );
      return this.find_link_at_cursor();
    }
  }
}

Editor.prototype.start_link = function () {
  return this.insert_link( "/notebooks/" + this.notebook_id + "?note_id=new" );
}

Editor.prototype.start_file_link = function () {
  return this.insert_link( "/files/new" );
}

Editor.prototype.end_link = function () {
  this.link_started = null;
  var link = this.find_link_at_cursor();

  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    this.exec_command( "unlink" );

    // necessary to actually end a link. the side-effect is that the cursor jumps to the
    // end of the link if it's not already there
    if ( link ) {
      var selection = this.iframe.contentWindow.getSelection();
      var sentinel = this.document.createTextNode( Editor.title_placeholder_char );
      insertSiblingNodesAfter( link, sentinel );
      selection.collapse( sentinel, 1 );
    }
  } else if ( this.document.selection ) { // browsers such as IE
    // if some text is already selected, unlink it and bail
    var range = this.document.selection.createRange();
    if ( range.text.length > 0 ) {
      this.exec_command( "unlink" );
      return;
    }

    // since execCommand() with "unlink" removes the entire link instead of just ending it, fake it
    // by appending a temporary span, selecting it, and then immediately removing it
    var span = this.document.createElement( "span" );
    span.innerHTML = "&nbsp;";
    range.parentElement().appendChild( span );
    range.moveToElementText( span );
    range.select();
    range.pasteHTML( "" );
  }

  return link;
}

Editor.prototype.find_link_at_cursor = function () {
  if ( this.iframe && this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    var link = selection.anchorNode;
    if ( !link ) return null;

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link )
        break;
    }

    if ( link != this.link_started )
      this.link_started = null;
    if ( link ) return link;

    // well, that didn't work, so try the selection's focus node instead
    link = selection.focusNode;

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link ) {
        this.link_started = null;
        return null;
      }
    }

    if ( link != this.link_started )
      this.link_started = null;
    return link;
  } else if ( this.document && this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    var link = range.parentElement();

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link ) {
        this.link_started = null;
        return null;
      }
    }

    if ( link != this.link_started )
      this.link_started = null;
    return link;
  }

  this.link_started = null;
  return null;
}

Editor.prototype.focus = function ( suppress_signal ) {
  if ( this.div && this.edit_enabled )
    this.claim_iframe();

  if ( this.iframe ) {
    addElementClass( this.iframe, "focused_note_frame" );

    if ( OPERA )
      this.iframe.focus();
    else
      this.iframe.contentWindow.focus();
  }

  if ( !suppress_signal )
    signal( this, "focused", this );
}

Editor.prototype.blur = function () {
  this.scrape_title();

  removeElementClass( this.iframe || this.div, "focused_note_frame" );
  if ( this.grabber )
    removeElementClass( this.grabber, "note_grabber_focused" );
}

Editor.prototype.release_iframe = function () {
  if ( !this.iframe )
    return;

  var contents = this.contents();

  disconnectAll( this.iframe.contentWindow );
  disconnectAll( this.iframe );
  disconnectAll( this.document.body );
  disconnectAll( this.document );
  this.iframe.editor = null;
  this.document = null;

  var static_contents = getFirstElementByTagAndClassName( "span", "static_note_contents", this.div );
  if ( static_contents )
    static_contents.innerHTML = contents;

  removeElementClass( this.div, "invisible" );
  addElementClass( this.iframe, "invisible" );
  setElementDimensions( this.iframe, { "h": 0 } );
  this.iframe = null;
}

Editor.prototype.contents = function () {
  if ( this.iframe && this.document && this.document.body )
    return this.document.body.innerHTML;

  if ( this.div ) {
    var static_contents = getFirstElementByTagAndClassName( "span", "static_note_contents", this.div );
    if ( static_contents )
      return static_contents.innerHTML;
  }

  return this.initial_text || "";
}

// return true if the given state_name is currently enabled, optionally using a given list of node
// names
Editor.prototype.state_enabled = function ( state_name, node_names, attribute_name ) {
  if ( !this.edit_enabled )
    return false;

  state_name = state_name.toLowerCase();
  if ( !node_names )
    node_names = this.current_node_names();

  for ( var i in node_names ) {
    var node_name = node_names[ i ];
    if ( node_name == state_name )
      return true;
  }

  return false;
}

DEFAULT_FOREGROUND_CODE = "#000000";
DEFAULT_BACKGROUND_CODE = "#ffffff";
WEBKIT_DEFAULT_COLOR_CODE = "rgba(0, 0, 0, 0)";

// return a list of names for all the nodes containing the cursor
Editor.prototype.current_node_names = function () {
  var node_names = new Array();

  if ( !this.edit_enabled || !this.iframe || !this.document )
    return node_names;

  // to determine whether the specified state is enabled, see whether the current selection is
  // contained (directly or indirectly) by a node of the appropriate type (e.g. "h3", "a", etc.)
  var node;
  if ( window.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    if ( selection.rangeCount > 0 )
      var range = selection.getRangeAt( 0 );
    else
      var range = this.document.createRange();
    node = range.endContainer;
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    node = range.parentElement();
  }

  while ( node ) {
    var name = node.nodeName.toLowerCase();

    if ( name == "body" )
      break;
    else if ( name == "strong" ) name = "b";
    else if ( name == "em" ) name = "i";
    else if ( name == "font" && node.getAttribute( "face" ) )
      name = "fontface";
    else if ( name == "font" && node.getAttribute( "size" ) )
      name = "fontsize";
    else if ( name == "font" && node.getAttribute( "color" ) )
      name = "color";
    else if ( name == "span" || name == "font" ) {
      var color = getStyle( node, "color" );
      var bg_color = getStyle( node, "background-color" );
      if ( ( color && color != "transparent" && color != DEFAULT_FOREGROUND_CODE ) ||
           ( bg_color && bg_color != "transparent" && bg_color != DEFAULT_BACKGROUND_CODE ) )
        name = "color";
    }

    if ( name != "a" || node.href )
      node_names.push( name );

    node = node.parentNode;
  }

  return node_names;
}

// return the current effective foreground and background colors as hex code strings
Editor.prototype.current_colors = function () {
  var foreground = null;
  var background = null;

  if ( !this.edit_enabled || !this.iframe || !this.document )
    return [ null, null ];

  var node;
  if ( window.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    if ( selection.rangeCount > 0 )
      var range = selection.getRangeAt( 0 );
    else
      var range = this.document.createRange();
    node = range.endContainer;
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();
    node = range.parentElement();
  }

  while ( node ) {
    var name = node.nodeName.toLowerCase();
    if ( name == "body" )
      break;

    if ( foreground == null && name == "font" && node.getAttribute( "color" ) ) {
      foreground = node.getAttribute( "color" );
    } else if ( name == "span" || name == "font" || name == "h3" ) {
      if ( foreground == null ) {
        foreground = getStyle( node, "color" )
        if ( foreground == "transparent" || foreground == DEFAULT_FOREGROUND_CODE ||
             foreground == WEBKIT_DEFAULT_COLOR_CODE )
          foreground = null;
      }
      if ( background == null ) {
        background = getStyle( node, "background-color" )
        if ( background == "transparent" || background == DEFAULT_BACKGROUND_CODE ||
             background == WEBKIT_DEFAULT_COLOR_CODE )
          background = null;
      }
    }

    if ( foreground && background )
      break;

    node = node.parentNode;
  }

  return [
    foreground ? Color.fromString( foreground ).toHexString() : null,
    background ? Color.fromString( background ).toHexString() : null
  ];
}

Editor.prototype.set_foreground_color = function( color_code ) {
  if ( GECKO ) this.exec_command( "styleWithCSS", true );
  this.exec_command( "forecolor", Color.fromString( color_code ).toHexString() );
  if ( GECKO ) this.exec_command( "styleWithCSS", false );

  this.cleanup_color_html();
}

Editor.prototype.set_background_color = function( color_code ) {
  if ( GECKO ) this.exec_command( "styleWithCSS", true );
  if ( MSIE )
    this.exec_command( "backcolor", Color.fromString( color_code ).toHexString() );
  else
    this.exec_command( "hilitecolor", Color.fromString( color_code ).toHexString() );
  if ( GECKO ) this.exec_command( "styleWithCSS", false );

  this.cleanup_color_html();
}

Editor.prototype.cleanup_color_html = function () {
  var fonts = getElementsByTagAndClassName( "font", null, this.document );

  // if we somehow end up with both a color attribute and a CSS style on a particular <font>
  // element, then remove the color attribute
  if ( !MSIE ) {
    for ( var i in fonts ) {
      var node = fonts[ i ];
      if ( node.hasAttribute( "style" ) && node.hasAttribute( "color" ) )
        node.removeAttribute( "color" );
    }
    return;
  }

  // for some reason, IE likes to add <font size=+0> tags when changing colors, which for some
  // reason appears to slightly increase the rendered font size
  for ( var i in fonts ) {
    var node = fonts[ i ];

    var size = node.getAttribute( "size" );
    if ( size == "+0" ) {
      node.removeAttribute( "size" );

      // unless there is at least one attribute, IE will add the "size=+0" right back on
      addElementClass( node, "nosize" );
    }
  }
}

Editor.prototype.shutdown = function( event ) {
  signal( this, "title_changed", this, this.title, null );
  this.closed = true;
  var note_controls = this.note_controls;

  if ( this.iframe ) {
    var iframe = this.iframe;
    // keeping a reference to the iframe allows removeElement( editor_node ) below to work in IE 6
    if ( !MSIE6 )
      this.iframe = null;
    disconnectAll( this );
    disconnectAll( this.delete_button );
    disconnectAll( this.changes_button );
    disconnectAll( this.tools_button );
    disconnectAll( this.hide_button );
    disconnectAll( this.grabber );
    disconnectAll( iframe );
  }

  if ( this.document ) {
    disconnectAll( this.document.body );
    disconnectAll( this.document );
  }

  disconnectAll( this.div );
  var holder = this.holder;

  blindUp( this.div, options = { "duration": 0.25, afterFinish: function () {
    try {
      removeElement( holder );
    } catch ( e ) { }
  } } );

  if ( !iframe )
    return;

  // overriding afterFinishInternal for the iframe prevents it from being set to "display: none",
  // which would break subsequent getSelection() calls
  iframe.editor = null;
  blindUp( iframe, options = { "duration": 0.25, afterFinishInternal: function () {
    try {
      addElementClass( iframe, "invisible" );
    } catch ( e ) { }
  } } );
}

Editor.prototype.summarize = function () {
  if ( this.document && this.document.body )
    return summarize_html( scrapeText( this.document.body ), this.title );

  if ( this.div )
    return summarize_html( scrapeText( this.div ), this.title );

  return "";
}

function summarize_html( html, title ) {
  var span = createDOM( "span", {} );
  span.innerHTML = html;
  var summary = strip( scrapeText( span ) );

  // remove the title (if any) from the summary text
  if ( title && summary.indexOf( title ) == 0 )
    summary = summary.substr( title.length );

  if ( summary.length == 0 )
    return null;

  var MAX_SUMMARY_LENGTH = 40;
  var word_count = 10;

  // split the summary on whitespace
  var words = summary.split( /\s+/ );

  function first_words( words, word_count ) {
    return words.slice( 0, word_count ).join( " " );
  }

  var truncated = false;
  summary = first_words( words, word_count );

  // find a summary less than MAX_SUMMARY_LENGTH and, if possible, truncated on a word boundary
  while ( summary.length > MAX_SUMMARY_LENGTH ) {
    word_count -= 1;
    summary = first_words( words, word_count );

    // if the first word is just ridiculously long, truncate it without finding a word boundary
    if ( word_count == 1 ) {
      summary = summary.substr( 0, MAX_SUMMARY_LENGTH );
      truncated = true;
      break;
    }
  }

  if ( truncated ||  word_count < words.length )
    summary += " ...";

  return summary;
}

// return the given html in a normal form. this makes html string comparisons more accurate
function normalize_html( html ) {
  if ( !html ) return html;

  // remove any "pulldown" attributes, which get added in IE whenever link.pulldown is set
  var normal_html = html.replace( /\s+pulldown="null"/g, "" );

  // convert absolute URLs to the server into relative URLs. accomplish this by removing, for
  // instance, "https://luminotes.com" from any URLs. this is necessary becuase IE insists on
  // converting relative link URLs to absolute URLs
  var base_url = window.location.protocol + "//" + window.location.host;
  normal_html = normal_html.replace( '="' + base_url + '/', '="/' );

  return normal_html;
}

Editor.prototype.dirty = function () {
  var original_html = normalize_html( this.initial_text )
  var current_html = normalize_html( this.contents() );

  if ( current_html == "" || current_html == original_html )
    return false;

  return true;
}

Editor.prototype.mark_clean = function () {
  this.initial_text = this.contents();
}

Editor.prototype.mark_dirty = function () {
  this.initial_text = null;
}

// convenience function for parsing a link that has an href URL containing a query string
function parse_query( link ) {
  if ( !link || !link.href )
    return new Array();

  return parseQueryString( link.href.split( "?" ).pop() );
}

// convenience function for getting a link's title (stripped of whitespace), either from a query
// argument in the href, from the actual link title, or from the link's href
function link_title( link, query ) {
  if ( link && link.target )
    return link.href;

  if ( !query )
    query = parse_query( link );

  var link_title = strip( query.title || scrapeText( link ) );

  // work around an IE quirk in which link titles are sometimes 0xa0
  if ( link_title.charCodeAt( 0 ) == 160 )
    return "";

  return link_title.replace( Editor.title_placeholder_pattern, "" );
}

function normalize_title( title ) {
  return title.replace( Editor.title_placeholder_pattern, "" ) || "untitled note";
}

function editor_by_id( note_id, revision ) {
  if ( revision ) {
    var iframe = getElement( "note_" + note_id + " " + revision );
    if ( !iframe && getElement( "note_" + note_id ) )
      return null;
  } else {
    var iframe = getElement( "note_" + note_id );
  }

  if ( iframe )
    return iframe.editor;

  var div = getElement( "static_note_" + note_id );

  if ( div ) {
    if ( revision && div.editor && div.editor.revision != revision )
      return null;

    return div.editor;
  }

  return null;
}
