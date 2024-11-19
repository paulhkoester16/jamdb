import pandas as pd
import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.exc import IntegrityError

from .db_error_handling import _db_error_factory


class DBHandler:

    def __init__(self, engine):
        self.engine = engine

    @classmethod
    def from_db_file(cls, db_file):
        engine = sqlalchemy.create_engine(
            f'sqlite:///{db_file}',
            connect_args={'check_same_thread': False}
        )
        return cls(engine)

    @staticmethod
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('pragma foreign_keys=ON')
    
    @property
    def engine(self):
        return self.__engine

    @property
    def Session(self):
        return self.__Session

    @engine.setter
    def engine(self, value):
        # sqlite dbs do NOT enable FKs on connection by default
        # Add listener to ensure they do get set.
        sqlalchemy.event.listen(value, 'connect', self._fk_pragma_on_connect)        
        self.__engine = value
        self.__Session = sqlalchemy.orm.sessionmaker(bind=self.__engine)    
    
    def _automap(self):
        AutomappedBase = automap_base()
        AutomappedBase.prepare(autoload_with=self.engine)
        self.__model_classes = dict(AutomappedBase.classes)
        self.__tables = AutomappedBase.metadata.tables        
    
    def model_classes(self, force_reload=False):
        if not force_reload:
            try:
                return self.__model_classes
            except AttributeError:
                pass
        self._automap()
        return self.__model_classes

    def tables(self, force_reload=False):
        if not force_reload:
            try:
                return self.__tables
            except AttributeError:
                pass
        self._automap()
        return self.__tables

    def read_table(self, table_name):
        with self.Session.begin() as session:
            result = pd.DataFrame(session.execute(sqlalchemy.text(f"SELECT * FROM {table_name}")).fetchall())
        return result
        
    def get_fks_for_table(self, table_name):
        inspector = sqlalchemy.inspect(self.engine)
    
        fk_constraints = []
        for fk in inspector.get_foreign_keys(table_name=table_name):
            fk["constrained_table"] = table_name
            fk_constraints.append(fk)
        return fk_constraints
    
    def insert(self, table_name, rows):
        try:
            with self.Session.begin() as session:
                table = self.tables()[table_name]
                session.execute(table.insert(), rows)

        except IntegrityError as exc:
            if not isinstance(rows, list):
                rows = [rows]

            error_class = _db_error_factory(exc)
            msg = error_class.error_messages_on_insert(self, table_name, rows, exc)

            if isinstance(msg, list):
                msg = "\n" + "\n".join([str(x) for x in msg])

            raise error_class(msg) from exc
    
    
    def update(self, table, *args, **kwargs):
        # Unclear if its worth adding our own `update` method -- won't do for now since all editing
        # of table happens in the ODS file, not the DB.  If we do support `update` will need to
        # to add some input cleansing and exception handling
        
        # with self.engine.connect() as conn:        
        #     conn.execute(
        #         table.update().values({"instrument_id": "trumpet"}).where(table.c.id == "paul_k:mando")    
        #     )
        raise NotImplementedError()

    def delete(self, table, *args, **kwargs):
        # Unclear if its worth adding our own `delete` method -- won't do for now since all editing
        # of table happens in the ODS file, not the DB.  If we do support `delete` will need to
        # to add some exception handling
        # with engine.connect() as conn:
        #     conn.execute(
        #         table.delete().where(table.c.id == "paul_k:drums")
        #     )
        raise NotImplementedError()
