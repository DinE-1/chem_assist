import gi,os,sys,mysql.connector
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk,Gdk,Gio,GLib
from mysql.connector import errorcode
import pages
import quiz

#construct dictionary from css file
def read_css_file(css_file_path):
    css_file=open(css_file_path,"r")
    css_file_contents=css_file.read()
    print(css_file_contents)
    mode="element"
    css_dict={}

    element=""
    key=""
    value=""
    for a in css_file_contents:
        #ignore lines starting with @
        if a=="@":
            mode="ignore"
        if mode=="ignore" and a==";":
            mode="element"
            continue
        #ignore whitespace character
        if a in [" ","\t","\n"] or mode=="ignore":
            continue
        #make the dictionary
        if a not in ["{","}",";",":"]:
            if mode=="element":
                element=element+a
            elif mode=="key":
                key=key+a
            elif mode=="value":
                value=value+a
        if a=="{":
            css_dict[element]={}
            mode="key"
        if a==":":
            mode="value"
        if a==";":
            css_dict[element][key]=value
            key,value="",""
            mode="key"
        if a=="}":
            element=""
            mode="element"
    return css_dict

#custom gtk application class containing helpful definitions
class Application(Gtk.Application):
    #window history
    window_history_limit=10
    window_history=[]

    #user preferences file name
    preference_file_name="user_preferences_chem_assist.conf"
    #default display
    default_display=Gdk.Display.get_default()

    current_file_path=__file__
    current_file_dir_parent=os.path.split(os.path.split(current_file_path)[0])[0] #get the parent directory of this file's directory
    if getattr(sys,'frozen',False):
        current_file_dir_parent=sys._MEIPASS
    #folder for styles,pictures
    css_dir=os.path.join(current_file_dir_parent,'styles')
    pics_dir=os.path.join(current_file_dir_parent,"pictures")

    #appearance(css)
    css_files_paths={
        "round_css":os.path.join(css_dir,'shape','rounded_edges.css'),
        'colorful_css':os.path.join(css_dir,"color","colors.css"),
        'black_shade_css':os.path.join(css_dir,'color','black_shade.css'),
        'images_css':os.path.join(css_dir,"images.css")
    }
    style_preference={
        "shapes":css_files_paths["round_css"],
        "colors":css_files_paths['colorful_css'],
        "images":css_files_paths['images_css']
    }    #set the style preference dictionary with some default preferences
    style_preference_default={
        "shapes":css_files_paths["round_css"],
        "colors":css_files_paths['colorful_css'],
        "images":css_files_paths['images_css']
    }
    other_styles_css_provider=Gtk.CssProvider.new()
    colors_css_provider=Gtk.CssProvider.new()
    images_css_provider=Gtk.CssProvider.new()
    current_css_providers={"shapes":other_styles_css_provider,"colors":colors_css_provider,"images":images_css_provider}

    #database
    db_name="chem_assist_db1"
    db_cursor=None
    database_object=None
    reactions_column_string_max_length=255

    #users
    users={'':'',"chem_assist_user":"chem_assist_user_password"}

    #columns for reactions table in database
    reactions_table_columns=("name","reactants","products","extra_info")

    #this function's code executed automatically
    def __init__(self):
        super().__init__(application_id="com.chem_assist_project.chem_assist")
        self.connect('activate',self.on_activate)
        self.connect('shutdown',self.on_close)
    #on activate app
    def on_activate(self,app):
        print("activated")

        #load preferences from the preferences file
        self.load_preference()

        #get monitor dimentions
        self.primary_monitor=self.default_display.get_monitors()[0]
        self.get_monitor_dimentions(self.primary_monitor)
        #load css files
        self.reload_styles()

        ##define actions
        quit_action=Gio.SimpleAction.new("quit",None)
        quit_action.connect('activate',self.close_page)
        self.add_action(quit_action)

        #current user action
        self.current_user_action=Gio.SimpleAction.new_stateful("current_user",GLib.VariantType.new("s"),GLib.Variant.new_string("chem_assist_user"))
        self.add_action(self.current_user_action)

        #appearance actions
        app_colors_action=Gio.SimpleAction.new_stateful('colors',GLib.VariantType.new('s'),GLib.Variant.new_string(self.style_preference["colors"]))
        self.add_action(app_colors_action)
        app_colors_action.connect('activate',self.css_reload_and_change_action_state)

        shapes_action=Gio.SimpleAction.new_stateful('shapes',GLib.VariantType.new('s'),GLib.Variant.new_string(self.style_preference['shapes']))
        self.add_action(shapes_action)
        shapes_action.connect('activate',self.css_reload_and_change_action_state)

        button_images_action = Gio.SimpleAction.new_stateful('images',GLib.VariantType.new('s'),GLib.Variant.new_string(self.style_preference['images']))
        self.add_action(button_images_action)
        button_images_action.connect('change_state',self.css_reload_and_change_action_state)

        #page opening actions
        open_reactions_page_action=Gio.SimpleAction.new("open_reactions_page",None)
        open_reactions_page_action.connect('activate',self.on_open_reactions_page)
        self.add_action(open_reactions_page_action)

        open_quiz_page_action=Gio.SimpleAction.new("open_quiz_page",None)
        open_quiz_page_action.connect('activate',self.open_quiz_page)
        self.add_action(open_quiz_page_action)

        open_quiz_action=Gio.SimpleAction.new('open_quiz',None)
        open_quiz_action.connect('activate',self.open_quiz)
        self.add_action(open_quiz_action)

        #connect to database action
        self.connect_to_db_action=Gio.SimpleAction.new("connect_to_db",None)
        self.connect_to_db_action.connect('activate',self.connect_to_db)
        self.add_action(self.connect_to_db_action)

        #open welcome page
        self.open_page(None,pages.welcome_page)
    
    #load saved preference from file
    def load_preference(self):
        #open and read the preferences file
        try:
            preference_file=open(os.path.join(os.path.dirname(os.path.dirname(__file__)),self.preference_file_name),'r')
        except Exception as err:
            print("Error opening preferences file",err)
            return False
        preferences=preference_file.read()
        preference_file.close()

        #do no process further is no preferences are detected
        if len(preferences) == 0 or preferences=="":
            return
        preferences=preferences.split('\n')
        #save the preferences in the form of preference=value into a dictionary as preference:value
        preference_dict={}
        for preference in preferences:
            #ignore lines starting with #
            if preference[0] == "#":
                continue
            
            #seperate the preference and value into a list
            preference=preference.split('=')

            #remove the quotes by removing the first and last character of the string
            preference[1]=preference[1][1:-1]

            if preference[1]==None:
                preference[1]=''
            preference_dict[preference[0]]=preference[1]

        self.style_preference.update(preference_dict)
        return preference_dict

    #pages open
    #reactions page open
    def on_open_reactions_page(self,caller_action,param):
        #open reactions page
        self.open_page(None,pages.reactions_display_page)
    #open quiz page
    def open_quiz_page(self,caller_action,param):
        self.open_page(None,pages.quiz_main_page)
    #open quiz from quiz module
    def open_quiz(self,caller_action,param):
        #connect to db
        connect_to_db_return=self.connect_to_db("None","None")
        if connect_to_db_return != True:
            #display error and exit function with return value as false
            if self.window_history[-1].message_box==True:
                self.props.active_window.message_label.set_text("database connection Error:"+str(connect_to_db_return))
            return connect_to_db_return
        create_db_return=self.create_db(self.db_cursor)
        if create_db_return != True:
            #display error and exit function with return value as false
            if self.window_history[-1].message_box==True:
                self.props.active_window.message_label.set_text("creating database error:"+str(create_db_return))
            return create_db_return
        #hide current window when quiz is open
        self.close_page()
        #open quiz.py quiz page
        quiz.main(self.database_object)
        #reshow current window
        self.open_page(None,pages.quiz_main_page)

    #close current page
    def close_page(self,caller_obj=None,page=None):            
        if page!=None:
            app.width=app.get_active_window().get_width()
            app.height=app.get_active_window().get_height()
            app.maximized=page.is_maximized()
            page.close()
        if page==None and self.get_active_window()!=None:
            self.props.active_window.close()
    #open page
    def open_page(app,caller_obj,page):
        app.close_page(page=app.props.active_window)

        app.window_history.append(page)
        app.window_history_size=len(app.window_history)
        #solve back button window loop problem
        if app.window_history_size > 2 and app.window_history[-1] == app.window_history[-3]:
            app.window_history.pop()
            app.window_history.pop()
        if app.window_history_size > 1 and app.window_history[-1] == app.window_history[-2]:
            app.window_history.pop()
        #trim window history if greater than limit
        if app.window_history_size>app.window_history_limit:
            del app.window_history[0]

        page=page(application=app)
        page.set_default_size(app.monitor_width/2,int(app.monitor_height/1.5))

        if len(app.window_history)>1:
            page.set_default_size(app.width,app.height)
            page.props.maximized=app.maximized

        #show the page to the user
        page.present()

    ##appearance
    #get monitor dimentions
    def get_monitor_dimentions(self,monitor):
        monitor_geometry=monitor.get_geometry()
        self.monitor_width=monitor_geometry.width
        self.monitor_height=monitor_geometry.height
    #load styles to context
    def reload_styles(self):
        for category,css_provider in self.current_css_providers.items():
            #if no style preference then remove from context
            if self.style_preference[category] == '':
                Gtk.StyleContext.remove_provider_for_display(self.default_display,self.current_css_providers[category])
                continue
            #load the css files to css provider
            self.current_css_providers[category].load_from_path(self.style_preference[category])
            #add css provider to context
            Gtk.StyleContext.add_provider_for_display(self.default_display,css_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    def css_reload_and_change_action_state(self,caller_action,state):
        #set the action state
        caller_action.set_state(state)
        #change the preference
        self.style_preference[caller_action.props.name]=state.get_string()
        #reload styles to apply the new style preference
        self.reload_styles()

    ##database
    #database connect and use
    def connect_to_db_server_and_create_db(self):
        #connect to db server and get cursor
        connect_to_db_return=self.connect_to_db(None,None)
        if connect_to_db_return != True:
            #display error and exit function
            print("[Error:database connection]")
            if self.window_history[-1].message_box==True:
                self.props.active_window.message_label.set_text("Error: "+str(connect_to_db_return))
            return connect_to_db_return
        #create database
        create_db_return=self.create_db(self.db_cursor)
        if create_db_return != True:
            #display error in main_menu page message box and exit the function
            if self.window_history[-1].message_box==True:
                self.props.active_window.message_label.set_text("Error: "+str(create_db_return))
            return create_db_return
        return True

    #create and use database
    def create_db(self,db_cursor):
        #create database
        try:
            db_cursor.execute(f'create database {self.db_name};')
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_DB_CREATE_EXISTS:
                #if database already exists
                msg_str=f"=>database {self.db_name} found"
                print(msg_str)
            else:
                print("Error while CREATING database:",err)
                return err
            print(f"=>created database {self.db_name}")
        #use database
        try:
            db_cursor.execute(f'use {self.db_name};')
        except mysql.connector.Error as err:
            print("Error while USING database",err)
            return err
        print(f'=>using database {self.db_name}')
        return True

    #connect to db and get cursor
    def connect_to_db(self,caller_action,parameter):
        #connect to server
        return_value_from_connect=self.connect_to_db_server()
        #do not contiunue if no cursor is available
        if return_value_from_connect != True:
            return return_value_from_connect
        #get cursor
        return_value_from_get_cursor=self.get_cursor_from_db_connection(self.database_object)
        #return the error if failed to get cursor
        if return_value_from_get_cursor !=True:
            return return_value_from_get_cursor
        return True

    #connect to database server
    def connect_to_db_server(self):

        #close any existing connection
        if self.database_object != None and self.database_object.is_connected():
            self.database_object.close()

        #please take backup of database before connecting with path as it may be deleted by this function
        connection_profile={
            "user":self.current_user_action.props.state.get_string(),
            "password":self.users[self.current_user_action.props.state.get_string()],
            "host":"localhost",
            "collation":"utf8mb4_general_ci"
        }
        try:
            self.database_object=mysql.connector.connect( **connection_profile)
        except mysql.connector.Error as err:
            message="Error while connecting to database: "+str(err)
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                message=f"Access denied for user {self.current_user_action.props.state.get_string()}"
            print(message)
            return err
        return True
    #get cursor from database connection
    def get_cursor_from_db_connection(self,db_connection_object):
        if db_connection_object == None:
            print(f"cannot get cursor, no database connection obj")
            return
        try:
            self.db_cursor=db_connection_object.cursor()
        except mysql.connector.Error as err:
            print(f"Error while getting cursor from database connection: {err}: Database_connection:{self.database_object.is_connected}")
            return err
        print("=>cursor connected")
        return True

    #create reactions table
    def create_reactions_table(self,db_cursor):
        col_max_len=self.reactions_column_string_max_length
        try:
            create_reactions_table_sql_command=f'''CREATE TABLE reactions(
                name varchar({col_max_len}) primary key,
                reactants varchar({col_max_len}),
                products varchar({col_max_len}),
                extra_info varchar({col_max_len}));'''
            db_cursor.execute(create_reactions_table_sql_command)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("=>reactions table found")
                return True
            else:
                print("eror while creating table \"reactions\"", err)
                return err
        print("=>created table 'reactions'")
        return True
    #save preferences while closing application
    def on_close(self,caller_object):
        #save the changed style preferences into a file
        preference_string=""
        for style,value in self.style_preference.items():
            if value != self.style_preference_default[style]:
                preference_string=preference_string+ '\n' + style + "='" + value + "'"
        preference_string=preference_string[1:]
        #write preferences to file
        self.write_string_to_file(preference_string)
    
    def write_string_to_file(self,string):
        #write a string to the preferences file
        try:
            #open file
            preference_file=open(self.preference_file_name,'w')
        except Execption as e:
            print(e)
            return False
        try:
            #write to file
            preference_file.write(string)
        except Exeption as e:
            print(e)
            return False
        return True

#Create an instance of Application class
app=Application()
app.run(None)