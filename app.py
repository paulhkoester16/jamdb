from flask import Flask, request, render_template
from wtforms import Form, SelectField, SubmitField

from jamdb.db import db_factory

DB_FILE = "data/jamming.db"

app = Flask(__name__) 


class GetRowForm(Form):

    table_name = SelectField("table_name")
    primary_key = SelectField("primary_key")
    submit = SubmitField("submit")

    def possible_table_choices(self):
        db_handler = db_factory(DB_FILE)
        choices = [("", "--choose--")]
        choices.extend(
            [
                (table_name, table_name) for table_name in db_handler.table_names()
            ]
        )
        return choices

    def possible_pk_choices(self, table_name):
        db_handler = db_factory(DB_FILE)
        choices = [("", "--choose--")]
        ent = db_handler.entities.get(table_name)
        if ent is not None:
            pk_name = ent.primary_key
            pks = list(db_handler.query(f"SELECT {pk_name} FROM {table_name}")[pk_name])
            choices.extend([(pk, pk) for pk in pks])
        return choices


@app.route('/', methods=["GET", "POST"])
def index():
    print(f"index:  {request.method}")
    return render_template("index.html")


@app.route('/get-row/', methods=["GET", "POST"])
def get_row():
    form = GetRowForm(request.form)
    print(f"get-row:  {request.method}")
    form.table_name.choices = form.possible_table_choices()
    if request.method == "POST" and form.table_name.data:
        form.primary_key.choices = form.possible_pk_choices(form.table_name.data)
    return render_template("get_row.html", form=form)


@app.route('/get-row-read/', methods=['POST']) 
def get_row_read():
    db_handler = db_factory(DB_FILE)
    print(f"get-row-read:  {request.method}")    
    data = request.form
    print(data)
    result = db_handler.get_row(
        table_name=data["table_name"],
        primary_key=data["primary_key"]
    )

    return result



if __name__ == '__main__':
    app.run()
