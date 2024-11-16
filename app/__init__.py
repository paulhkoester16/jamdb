from flask import Flask
from flask_graphql import GraphQLView

from jamdb.graphene import GrapheneSQLSession


def init_app(config_filename=None):
    app = Flask(__name__, instance_relative_config=True)
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    graphene_session = GrapheneSQLSession.from_sqlite_file()
    
    graphql_view = GraphQLView.as_view(
        "graphql",
        schema=graphene_session.schema,
        graphiql=True,
        get_context=lambda: {'session': graphene_session.session}
    )
    app.add_url_rule("/graphql", view_func=graphql_view, methods=["GET", "POST", "PUT", "DELETE"])
    
    with app.app_context():
        from . import routes  # other routes defined in there
        return app
