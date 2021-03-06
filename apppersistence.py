import sqlite3

class Storage:
    '''This is to abstract persistence logic from the main application'''

    app_persistence_db = "../depmandb/depman.db"

    def __init__(self):
        self.init_tables()

    def get_conn(self):
        return sqlite3.connect(self.app_persistence_db)

    def init_tables(self):
        conn = self.get_conn()
        with conn:
            table_exists = False
            cursor = conn.cursor()
            try:
                # If you are checking for the existence of an in-memory (RAM) table, then in the query use sqlite_temp_master instead of sqlite_master.
                cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='workload_controller'")
                if cursor.fetchone()[0]==1:
                    print('Tabled exists.')
                    table_exists = True
            except:
                print('Table does not exist yet')

            if not table_exists:
                cursor.execute('''CREATE TABLE workload_controller (id INTEGER PRIMARY KEY AUTOINCREMENT, type text, controller_name text, controller_project text, microservice_name text, microservice_artifact_version text, microservice_api_version text, contracts_provided text, contracts_required text, deployment_completed bool)''')
        return

    def flush_tables(self):
        conn = self.get_conn()
        with conn:
            cursor = conn.cursor()
            cursor.execute("delete from workload_controller")
        print("workload_controller flushed")

    def create_controller(self, c):
        conn = self.get_conn()
        with conn:
            cursor = conn.cursor()
            sql = """insert into workload_controller
                (type, controller_name, controller_project, microservice_name, microservice_artifact_version, microservice_api_version, contracts_provided, contracts_required, deployment_completed)
                values(?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            data_tuple = (c.type, c.controller_name, c.controller_project, c.microservice_name, c.microservice_artifact_version, c.microservice_api_version, c.contracts_provided, c.contracts_required,c.deployment_completed)
            cursor.execute(sql, data_tuple)
        print("Created Controller")

    def update_controller(self, c):
        conn = self.get_conn()
        with conn:
            cursor = conn.cursor()
            sql = """update workload_controller
                    set microservice_name = ?, microservice_artifact_version = ?, microservice_api_version = ?, contracts_provided =?, contracts_required = ?, deployment_completed =?
                    where id = ?"""
            data_tuple = (c.microservice_name, c.microservice_artifact_version, c.microservice_api_version, c.contracts_provided, c.contracts_required,c.deployment_completed,c.id)
            cursor.execute(sql, data_tuple)
        print("Updated Controller")

    def delete_controller(self, c):
        delete_controller_by_id(c["id"])

    def delete_controller_by_id(self, id):
        conn = self.get_conn()
        with conn:
            cursor = conn.cursor()
            cursor.execute("delete from workload_controller where id=?", (id,))
        print("Deleted Controller")

    def select_controller_by_key(self, namespace, type, name):
        conn = self.get_conn()
        with conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("select * from workload_controller where controller_project = ? and type = ? and controller_name = ?", (namespace, type, name))
            return self.convert_to_controller(cursor.fetchone())

    def select_controller_by_id(self, id):
        conn = self.get_conn()
        with conn:
            cursor = conn.cursor()
            cursor.execute("select * from workload_controller where id=?", (id,))
            return cursor.fetchone()

    # TODO add some try/catch statements for safety
    def select_controllers(self):
        conn = self.get_conn()
        with conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("select * from workload_controller")
            return cursor.fetchall()

    def select_incomplete_controllers(self):
        conn = self.get_conn()
        with conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("select * from workload_controller where deployment_completed = 0")
            return cursor.fetchall()

    # Returns a map of contracts
    def select_contracts(self):
        conn = self.get_conn()
        with conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("select controller_project, contracts_provided from workload_controller where deployment_completed = 1")
            records = cursor.fetchall()

            mapped_results = {}
            for rows in records:
                sanitized = mapped_results.get(rows["controller_project"], [])
                for r in rows["contracts_provided"].split(","):
                    if r.strip() not in sanitized:
                        sanitized.append(r.strip())
                mapped_results[rows["controller_project"]] = sanitized

            return mapped_results

    ## returns a list of contract names
    def select_contracts_by_env(self, env):
        conn = self.get_conn()
        with conn:
            cursor = conn.cursor()
            cursor.execute("select contracts_provided from workload_controller where controller_project like ? and deployment_completed = 1", ("%-"+env,))
            records = cursor.fetchall()

            sanitized = []
            for rows in records:
                for r in rows[0].split(","):
                    if r.strip() not in sanitized:
                        sanitized.append(r.strip())

            return sanitized

    def convert_to_controller(self, obj):
        if obj is None:
            return None

        ctr = Workload_Controller()
        ctr.id = obj["id"]
        ctr.type = obj["type"]
        ctr.controller_name = obj["controller_name"]
        ctr.controller_project = obj["controller_project"]
        ctr.microservice_name = obj["microservice_name"]
        ctr.microservice_api_version = obj["microservice_api_version"]
        ctr.microservice_artifact_version = obj["microservice_artifact_version"]
        ctr.contracts_provided = obj["contracts_provided"]
        ctr.contracts_required = obj["contracts_required"]
        ctr.deployment_completed = obj["deployment_completed"]
        return ctr

class Workload_Controller:
    '''This encapsulates a Workload Controller object'''
    def __init__(self):
        self.id = None
        self.type = None
        self.controller_name = None
        self.controller_project = None
        self.microservice_name = None
        self.microservice_artifact_version = None
        self.microservice_api_version = None
        self.contracts_provided = None
        self.contracts_required = None
        self.deployment_completed = None
