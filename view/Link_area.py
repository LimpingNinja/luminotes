from Tags import Div, Span, H4, A, Strong, Img
from Rounded_div import Rounded_div
from Search_form import Search_form


class Link_area( Div ):
  def __init__( self, notebooks, notebook, parent_id, notebook_path, user ):
    linked_notebooks = [ nb for nb in notebooks if
      ( nb.read_write or not nb.name.startswith( u"Luminotes" ) ) and
      nb.name not in ( u"trash" ) and
      nb.deleted is False
    ]

    Div.__init__(
      self,
      Div(
        Div(
          H4( u"this notebook", id = u"this_notebook_area_title" ),
          Div(
            Search_form(),
            class_ = u"link_area_item",
          ),

          ( notebook.name != u"Luminotes" ) and Div(
            A(
              u"download as html",
              href = u"/notebooks/download_html/%s" % notebook.object_id,
              id = u"download_html_link",
              title = u"Download a stand-alone copy of the entire wiki notebook.",
            ),
            class_ = u"link_area_item",
          ) or None,

          Div(
            A(
              u"subscribe to rss",
              href = u"%s?rss" % notebook_path,
              id = u"rss link",
              title = u"Subscribe to the RSS feed for " + \
                ( ( notebook.name == u"Luminotes blog" ) and u"the Luminotes blog." or u"this notebook." ),
            ),
            A(
              Img( src = u"/static/images/rss.png", width = u"14", height = u"14", class_ = u"rss_image" ),
              href = u"%s?rss" % notebook_path,
              title = u"Subscribe to the RSS feed for " + \
                ( ( notebook.name == u"Luminotes blog" ) and u"the Luminotes blog." or u"this notebook." ),
            ),
            class_ = u"link_area_item",
          ),

          notebook.read_write and Span(
            ( notebook.owner and notebook.name != u"trash" ) and Div(
              A(
                u"rename notebook",
                href = u"#",
                id = u"rename_notebook_link",
                title = u"Change the name of this notebook.",
              ),
              class_ = u"link_area_item",
            ) or None,

            ( notebook.owner and notebook.name != u"trash" ) and Div(
              A(
                u"delete notebook",
                href = u"#",
                id = u"delete_notebook_link",
                title = u"Move this notebook to the trash.",
              ),
              class_ = u"link_area_item",
            ) or None,

            Div(
              A(
                u"add new notebook",
                href = u"#",
                id = u"add_notebook_link",
                title = u"Create a new wiki notebook.",
              ),
              class_ = u"link_area_item",
            ),

            ( notebook.owner and user.username ) and Div(
              A(
                u"share",
                href = u"#",
                id = u"share_notebook_link",
                title = u"Share this notebook with others.",
              ),
              class_ = u"link_area_item",
            ) or None,

            notebook.trash_id and Div(
              A(
                u"trash",
                href = u"/notebooks/%s?parent_id=%s" % ( notebook.trash_id, notebook.object_id ),
                id = u"trash_link",
                title = u"Look here for notes you've deleted.",
              ),
              class_ = u"link_area_item",
            ) or None,

            ( notebook.name == u"trash" ) and Rounded_div(
              u"trash_notebook",
              A(
                u"trash",
                href = u"#",
                id = u"trash_link",
                title = u"Look here for notes you've deleted.",
              ),
              class_ = u"link_area_item",
            ) or None,
          ) or None,

          id = u"this_notebook_area",
        ),

        Div(
          ( len( linked_notebooks ) > 0 ) and H4( u"notebooks", id = u"notebooks_area_title" ) or None,
          [ ( nb.object_id == notebook.object_id ) and Rounded_div(
            u"current_notebook",
            A(
              nb.name,
              href = u"/notebooks/%s" % nb.object_id,
              id = u"notebook_%s" % nb.object_id,
            ),
            ( len( linked_notebooks ) > 1 ) and Span(
              Img( src = u"/static/images/up_arrow.png", width = u"20", height = u"17", id = u"current_notebook_up" ),
              Img( src = u"/static/images/down_arrow.png", width = u"20", height = u"17", id = u"current_notebook_down" ),
              Span( id = "current_notebook_up_hover_preload" ),
              Span( id = "current_notebook_down_hover_preload" ),
            ) or None,
            class_ = u"link_area_item",
          ) or
          Div(
            A(
              nb.name,
              href = u"/notebooks/%s" % nb.object_id,
              id = u"notebook_%s" % nb.object_id,
            ),
            class_ = u"link_area_item",
          ) for nb in linked_notebooks ],
          id = u"notebooks_area"
        ),

        Div(
          id = u"storage_usage_area",
        ),
        id = u"link_area_holder",
      ),
      id = u"link_area",
    )
