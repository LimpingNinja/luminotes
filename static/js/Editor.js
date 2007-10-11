function Editor( id, notebook_id, note_text, deleted_from_id, revision, read_write, startup, highlight, focus ) {
  this.id = id;
  this.notebook_id = notebook_id;
  this.initial_text = note_text;
  this.deleted_from_id = deleted_from_id || null;
  this.revision = revision;
  this.revisions_list = new Array(); // cache for this note's list of revisions, loaded from the server on-demand
  this.read_write = read_write;
  this.startup = startup || false; // whether this Editor is for a startup note
  this.init_highlight = highlight || false;
  this.init_focus = focus || false;
  this.closed = false;
  this.link_started = null;
  var iframe_id = "note_" + id;

  var self = this;
  this.document = null;
  this.iframe = createDOM( "iframe", {
    "src": "/static/html/blank_note.html",
    "frameBorder": "0",
    "scrolling": "no",
    "id": iframe_id,
    "name": iframe_id,
    "class": "note_frame",
    "onresize": function () { setTimeout( function () { self.resize() }, 50 ); }
  } );
  this.iframe.editor = this;
  this.title = null;

  if ( read_write ) {
    this.delete_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "delete_" + iframe_id,
      "value": "delete" + ( this.deleted_from_id ? " forever" : "" ),
      "title": "delete note [ctrl-d]"
    } );
    connect( this.delete_button, "onclick", function ( event ) { signal( self, "delete_clicked", event ); } );

    this.changes_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "changes_" + iframe_id,
      "value": "changes",
      "title": "previous revisions"
    } );
    connect( this.changes_button, "onclick", function ( event ) { signal( self, "changes_clicked", event ); } );

    if ( this.deleted_from_id ) {
      this.undelete_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "undelete_" + iframe_id,
        "value": "undelete",
        "title": "undelete note"
      } );
      connect( this.undelete_button, "onclick", function ( event ) { signal( self, "undelete_clicked", event ); } );
    } else {
      this.options_button = createDOM( "input", {
        "type": "button",
        "class": "note_button",
        "id": "options_" + iframe_id,
        "value": "options",
        "title": "note options"
      } );
      connect( this.options_button, "onclick", function ( event ) { signal( self, "options_clicked", event ); } );
    }
  }

  if ( !this.deleted_from_id && ( read_write || !startup ) ) {
    this.hide_button = createDOM( "input", {
      "type": "button",
      "class": "note_button",
      "id": "hide_" + iframe_id,
      "value": "hide",
      "title": "hide note [ctrl-h]"
    } );
    connect( this.hide_button, "onclick", function ( event ) { signal( self, "hide_clicked", event ); } );
  }

  this.note_controls = createDOM( "span", { "class": "note_controls" },
    this.delete_button ? this.delete_button : null,
    this.delete_button ? " " : null,
    this.changes_button ? this.changes_button : null,
    this.changes_button ? " " : null,
    this.options_button ? this.options_button : null,
    this.options_button ? " " : null,
    this.undelete_button ? this.undelete_button : null,
    this.undelete_button ? " " : null,
    this.hide_button ? this.hide_button : null
  );

  appendChildNodes( "notes", this.note_controls );
  appendChildNodes( "notes", this.iframe );

  connect( this.iframe, "onload", function ( event ) { self.init_document(); } );
}

// second stage of construction, invoked by editor_loaded(). do not call directly
Editor.prototype.init_document = function () {
  var self = this; // necessary so that the member functions of this editor object are used

  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    this.document = this.iframe.contentDocument;

    if ( this.read_write )
      this.document.designMode = "On";    

    setTimeout( function () { self.finish_init(); }, 1 );
  } else { // browsers such as IE
    this.document = this.iframe.contentWindow.document;

    if ( this.read_write ) {
      this.document.designMode = "On";   
      // work-around for IE bug: reget the document after designMode is turned on
      this.document = this.iframe.contentWindow.document;
    }
    setTimeout( function () { self.finish_init(); }, 100 );
  }
}

// third and final stage of construction, invoked by init_document(). do not call directly
Editor.prototype.finish_init = function () {
  if ( !this.initial_text )
    this.initial_text = "<h3>";

  this.insert_html( this.initial_text );

  var self = this; // necessary so that the member functions of this editor object are used
  if ( this.read_write ) {
    connect( this.document, "onkeydown", function ( event ) { self.key_pressed( event ); } );
    connect( this.document, "onkeyup", function ( event ) { self.key_released( event ); } );
    connect( this.document, "onblur", function ( event ) { self.blurred( event ); } );
    connect( this.document, "onfocus", function ( event ) { self.focused( event ); } );
    connect( this.document.body, "onblur", function ( event ) { self.blurred( event ); } );
    connect( this.document.body, "onfocus", function ( event ) { self.focused( event ); } );
  }

  connect( this.document, "onclick", function ( event ) { self.mouse_clicked( event ); } );

  // special-case: connect any submit buttons within the contents of this note
  var signup_button = withDocument( this.document, function () { return getElement( "signup_button" ); } );
  if ( signup_button ) {
    var signup_form = withDocument( this.document, function () { return getElement( "signup_form" ); } );
    connect( signup_button, "onclick", function ( event ) {
      signal( self, "submit_form", "/users/signup", signup_form ); event.stop();
    } );
  }

  var login_button = withDocument( this.document, function () { return getElement( "login_button" ); } );
  if ( login_button ) {
    var login_form = withDocument( this.document, function () { return getElement( "login_form" ); } );
    connect( login_button, "onclick", function ( event ) {
      signal( self, "submit_form", "/users/login", login_form ); event.stop();
    } );
  }

  var send_reset_button = withDocument( this.document, function () { return getElement( "send_reset_button" ); } );
  if ( send_reset_button ) {
    var send_reset_form = withDocument( this.document, function () { return getElement( "send_reset_form" ); } );
    connect( send_reset_button, "onclick", function ( event ) {
      signal( self, "submit_form", "/users/send_reset", send_reset_form ); event.stop();
    } );
  }

  var reset_button = withDocument( this.document, function () { return getElement( "reset_button" ); } );
  if ( reset_button ) {
    var reset_form = withDocument( this.document, function () { return getElement( "reset_form" ); } );
    connect( reset_button, "onclick", function ( event ) {
      signal( self, "submit_form", "/users/reset_password", reset_form ); event.stop();
    } );
  }

  if ( this.iframe.contentDocument ) { // browsers such as Firefox
    if ( this.read_write ) this.exec_command( "styleWithCSS", false );
  }

  this.resize();
  if ( this.init_highlight ) self.highlight();

  this.scrape_title();
  if ( this.init_focus )
    this.focus();

  signal( self, "init_complete" );
}

Editor.prototype.highlight = function ( scroll ) {
  if ( scroll == undefined )
    scroll = true;

  if ( /Opera/.test( navigator.userAgent ) ) { // MochiKit's Highlight is broken in Opera
    if ( scroll ) ScrollTo( this.note_controls );
    pulsate( this.iframe, options = { "pulses": 1, "duration": 0.5 } );
  } else if ( this.iframe.contentDocument ) { // browsers such as Firefox
    if ( scroll ) ScrollTo( this.note_controls );
    Highlight( this.iframe, options = { "queue": { "scope": "highlight", "limit": 1 } } );
  } else { // browsers such as IE
    if ( scroll ) ScrollTo( this.note_controls );
    if ( this.document && this.document.body )
      Highlight( this.document.body, options = { "queue": { "scope": "highlight", "limit": 1 } } );
  }
}

Editor.prototype.exec_command = function ( command, parameter ) {
  command = command.toLowerCase();

  if ( command == "h3" ) {
    if ( this.state_enabled( "h3" ) )
      this.document.execCommand( "formatblock", false, "normal" );
    else
      this.document.execCommand( "formatblock", false, "<h3>" );
    return;
  }

  this.document.execCommand( command, false, parameter );
}

Editor.prototype.insert_html = function ( html ) {
  if ( html.length == 0 ) return;

  if ( !this.read_write ) {
    this.document.body.innerHTML = html;
    return;
  }

  try { // browsers supporting insertHTML command, such as Firefox
    this.document.execCommand( "insertHTML", false, html );

    // for some reason, appending an empty span improves formatting
    spans = getElementsByTagAndClassName( "span", null, parent = this.document );
    if ( spans.length == 0 ) {
      var span = this.document.createElement( "span" );
      this.document.body.appendChild( span );
    }
  } catch ( e ) { // browsers that don't support insertHTML, such as IE
    this.document.body.innerHTML = html;
  }
}

// resize the editor's frame to fit the dimensions of its content
Editor.prototype.resize = function () {
  var dimensions;
  // TODO: find a better way to determine which dimensions to use than just checking for contentDocument
  if ( this.iframe.contentDocument ) { // Firefox
    dimensions = { "h": elementDimensions( this.document.documentElement ).h };
  } else { // IE
    if ( !this.document ) return;
    dimensions = { "h": this.document.body.scrollHeight };
  }

  setElementDimensions( this.iframe, dimensions );
}

Editor.prototype.key_pressed = function ( event ) {
  signal( this, "key_pressed", this, event );

  this.resize();
}

Editor.prototype.key_released = function ( event ) {
  this.resize();

  // if ctrl keys are released, bail
  var code = event.key().code;
  if ( event.modifier().ctrl )
    return;

  signal( this, "state_changed", this );
}

Editor.prototype.mouse_clicked = function ( event ) {
  this.link_started = null;

  // update the state no matter what, in case the cursor has moved
  if ( this.read_write )
    signal( this, "state_changed", this );

  // we only want to deal with left mouse button clicks
  if ( event.mouse().button.middle || event.mouse().button.right )
    return;

  // search through the tree of elements containing the clicked target. if a link isn't found, bail
  var link = event.target()
  while ( link.nodeName != "A" ) {
    link = link.parentNode;
    if ( !link )
      return;
  }
  if ( !link.href ) return;

  // links with targets are considered to be external links pointing outside of this wiki
  if ( link.target ) {
    // if this is a read-only editor, bail and let the browser handle the link normally
    if ( !this.read_write ) return;
    
    // otherwise, this is a read-write editor, so we've got to launch the external link ourselves.
    // note that this ignores what the link target actually contains and assumes it's "_new"
    window.open( link.href );
    event.stop();
    return;
  }

  event.stop();

  // load the note corresponding to the clicked link
  var query = parse_query( link );
  var title = link_title( link, query );
  var id = query.note_id;
  signal( this, "load_editor", title, id, null, link );
}

Editor.prototype.scrape_title = function () {
  // scrape the note title out of the editor
  var heading = getFirstElementByTagAndClassName( "h3", null, this.document );
  if ( !heading ) return;
  var title = scrapeText( heading );

  // issue a signal that the title has changed and save off the new title
  signal( this, "title_changed", this, this.title, title );
  this.title = title;
}

Editor.prototype.focused = function () {
  signal( this, "focused", this );
}

Editor.prototype.blurred = function () {
  this.scrape_title();
}

Editor.prototype.empty = function () {
  if ( !this.document || !this.document.body )
    return true; // consider it empty as of now

  return ( scrapeText( this.document.body ).length == 0 );
}

Editor.prototype.start_link = function () {
  // get the current selection, which is the link title
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();

    // if no text is selected, then insert a link with a placeholder nbsp as the link title, and
    // then immediately remove the link title once the link is created
    if ( selection.toString().length == 0 ) {
      this.insert_html( '<span id="placeholder_title"> </span>' );
      var placeholder = withDocument( this.document, function () { return getElement( "placeholder_title" ); } );
      selection.selectAllChildren( placeholder );

      this.exec_command( "createLink", "/notebooks/" + this.notebook_id + "?note_id=new" );

      // hack to prevent Firefox from erasing spaces before links that happen to be at the end of list items
      var sentinel = createDOM( "span" );
      insertSiblingNodesBefore( placeholder.parentNode, sentinel );
      this.link_started = placeholder.parentNode;

      // nuke the link title and collapse the selection, yielding a tasty new link that's completely
      // titleless and unselected
      removeElement( placeholder );
    // otherwise, just create a link with the selected text as the link title
    } else {
      this.link_started = null;
      this.exec_command( "createLink", "/notebooks/" + this.notebook_id + "?note_id=new" );
      var link = this.find_link_at_cursor();
      signal( this, "resolve_link", link_title( link ), link );
    }
  } else if ( this.document.selection ) { // browsers such as IE
    var range = this.document.selection.createRange();

    // if no text is selected, then insert a link with a placeholder space as the link title, and
    // then select it
    if ( range.text.length == 0 ) {
      range.text = " ";
      range.moveStart( "character", -1 );
      range.select();
      this.exec_command( "createLink", "/notebooks/" + this.notebook_id + "?note_id=new" );
      this.link_started = this.find_link_at_cursor();
    } else {
      this.link_started = null;
      this.exec_command( "createLink", "/notebooks/" + this.notebook_id + "?note_id=new" );
      var link = this.find_link_at_cursor();
      signal( this, "resolve_link", link_title( link ), link );
    }
  }
}

Editor.prototype.end_link = function () {
  this.link_started = null;
  var link = this.find_link_at_cursor();

  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    this.exec_command( "unlink" );
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

  signal( this, "resolve_link", link_title( link ), link );
  return link;
}

Editor.prototype.find_link_at_cursor = function () {
  if ( this.iframe.contentWindow && this.iframe.contentWindow.getSelection ) { // browsers such as Firefox
    var selection = this.iframe.contentWindow.getSelection();
    var link = selection.anchorNode;

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
  } else if ( this.document.selection ) { // browsers such as IE
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

Editor.prototype.focus = function () {
  if ( /Opera/.test( navigator.userAgent ) )
    this.iframe.focus();
  else
    this.iframe.contentWindow.focus();
}

// return true if the specified state is enabled
Editor.prototype.state_enabled = function ( state_name ) {
  if ( !this.read_write ) return false;

  state_name = state_name.toLowerCase();

  var format_block = this.document.queryCommandValue( "formatblock" ).toLowerCase();
  var heading = ( format_block == "h3" || format_block == "heading 3" );

  if ( state_name == "h3" )
    return heading;

  if ( state_name == "bold" && heading )
    return false;

  // to determine if we're within a link, see whether the current selection is contained (directly
  // or indirectly) by an "A" node
  if ( state_name == "createlink" ) {
    var link;
    if ( window.getSelection ) { // browsers such as Firefox
      var selection = this.iframe.contentWindow.getSelection();
      var range = selection.getRangeAt( 0 );
      link = range.endContainer;
    } else if ( this.document.selection ) { // browsers such as IE
      var range = this.document.selection.createRange();
      link = range.parentElement();
    }

    while ( link.nodeName != "A" ) {
      link = link.parentNode;
      if ( !link )
        return false;
    }
    if ( !link.href )
      return false;

    return true;
  }

  return this.document.queryCommandState( state_name )
}

Editor.prototype.contents = function () {
  return this.document.body.innerHTML;
}

Editor.prototype.shutdown = function( event ) {
  signal( this, "title_changed", this, this.title, null );
  this.closed = true;
  var iframe = this.iframe;
  var note_controls = this.note_controls;
  disconnectAll( this );
  disconnectAll( this.delete_button );
  disconnectAll( this.changes_button );
  disconnectAll( this.options_button );
  disconnectAll( this.hide_button );
  disconnectAll( iframe );

  if ( this.document ) {
    disconnectAll( this.document.body );
    disconnectAll( this.document );
  }

  blindUp( iframe, options = { "duration": 0.5, afterFinish: function () {
    try {
      removeElement( note_controls );
      removeElement( iframe );
    } catch ( e ) { }
  } } );
}

// convenience function for parsing a link that has an href URL containing a query string
function parse_query( link ) {
  if ( !link || !link.href )
    return new Array();

  return parseQueryString( link.href.split( "?" ).pop() );
}

// convenience function for getting a link's title (stripped of whitespace), either from a query
// argument in the href or from the actual link title
function link_title( link, query ) {
  if ( !query )
    query = parse_query( link );

  var link_title = strip( query.title || scrapeText( link ) );

  // work around an IE quirk in which link titles are sometimes 0xa0
  if ( link_title.charCodeAt( 0 ) == 160 )
    return "";

  return link_title;
}
