from flask import Flask

def init_app(config_filename=None):
    app = Flask(__name__, instance_relative_config=True)
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    #schema = ...  # but execute requires the sql engine context -- is that an other arge?
    #graphql_view = GraphQLView.as_view("graphql", schema=schema, graphiql=True)
    #app.add_url_rule("/graphql", view_func=graphql_view, methods=["GET", "POST", "PUT", "DELETE"])

    with app.app_context():
        from . import routes  # other routes defined in there
        return app
