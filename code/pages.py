import os,gi,mysql.connector
gi.require_version("Gtk","4.0")
from gi.repository import Gtk,Gio,GObject,GLib

#read a file
def read_file(file_path):
    try:
        file=open(file_path,'r')
    except Exception as e:
        print(e)
    file_contents=file.read()
    file.close()
    return file_contents

#return the list of children of a widget
def get_children(parent):
    children=[]
    children.append(parent.get_first_child())
    while True:
        sibling=children[-1].get_next_sibling()
        if sibling==None:
            break
        children.append(sibling)
    return children
#add a css class to children of a widget
def add_css_class_to_children(parent,css_class):
    children=get_children(parent)
    for i in children:
        i.add_css_class(css_class)

#store reaction data
class reaction_info(GObject.Object):
    def __init__(self,name,reactant,product,extra_info):
        super().__init__()
        self.name=name
        self.reactants=reactant
        self.products=product
        self.extra_info=extra_info
#header bar        
class header_bar(Gtk.HeaderBar):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
    def set_titlebar(self,page,settings=True,back_button=True):
        page.set_titlebar(self())

        if settings==True:
            #settings button
            self.settings_button=Gtk.Button.new()
            self.settings_button.add_css_class("settings_button")
            self.settings_button.add_css_class("icon_button")
            #add to headerbar
            page.props.titlebar.pack_end(page.props.titlebar.settings_button)
            page.props.titlebar.settings_button.connect('clicked',page.props.application.open_page,settings_page)
        if back_button==True:
            #back button
            self.back_button=Gtk.Button.new()
            self.back_button.add_css_class("back_button")
            self.back_button.add_css_class("icon_button")
            #add to headerbar
            page.props.titlebar.back_button.connect('clicked',page.props.application.open_page,page.props.application.window_history[-2])
            page.props.titlebar.pack_start(page.props.titlebar.back_button)
##pages
#welcome page
class welcome_page(Gtk.ApplicationWindow):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="welcome!")

        self.set_decorated(False)
        #event controller
        event_controller=Gtk.EventControllerKey()
        self.add_controller(event_controller)
        #welcome message
        welcome_message=Gtk.Label.new()
        self.set_child(welcome_message)
        welcome_message.set_markup(\
            f"""<span font-size='{self.props.application.monitor_width/50}pt'>Welcome to Chemistry assistant!</span>
            <span>{"\n"*int(self.props.application.monitor_height/100)}</span>
            <span font-size="{self.props.application.monitor_width/120}pt">Press any key to start!</span>""")
        #event controller function
        event_controller.connect('key-pressed',self.do_key_pressed)
    def do_key_pressed(self,*args):
        self.props.application.open_page(None,main_menu_page)

#settings page
class settings_page(Gtk.ApplicationWindow):
    message_box=True
    open_page=""
    current_page=''

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="settings")
        self.current_page=''

        header_bar.set_titlebar(header_bar,self,settings=False)

        ##layout
        self.main_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,0)
        self.set_child(self.main_box)

        #scrolling support for window
        side_panel_scroll=Gtk.ScrolledWindow.new()
        self.settings_page_scroll=Gtk.ScrolledWindow.new()

        #properties
        side_panel_scroll.set_propagate_natural_width(True) #do not shrink button width when space is available

        self.settings_page_scroll.set_propagate_natural_width(True)
        self.settings_page_scroll.set_hexpand(True)

        #boxes
        settings_categories_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,0)
        self.settings_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        #scroll support
        side_panel_scroll.set_child(settings_categories_box)
        self.settings_page_scroll.set_child(self.settings_box)

        #add to page
        self.main_box.append(side_panel_scroll)
        self.main_box.append(self.settings_page_scroll)

        #side panel buttons
        appearance_settings_button=Gtk.Button.new_with_label("Appearance")
        db_settings_button=Gtk.Button.new_with_label("Database")
        users_settings_button=Gtk.Button.new_with_label("Users")

        #button properties
        settings_categories_box.append(appearance_settings_button)
        settings_categories_box.append(db_settings_button)
        settings_categories_box.append(users_settings_button)
        add_css_class_to_children(settings_categories_box,"settings_categories_box")

        self.settings_box.set_hexpand(True)
        #button functions
        appearance_settings_button.connect('clicked',self.appearance_display)
        users_settings_button.connect('clicked',self.users_display)
        db_settings_button.connect('clicked',self.db_settings_display)

        ##actions
        #users selection button
        user_button_activate_action=Gio.SimpleAction.new_stateful('current_user_button',GLib.VariantType.new("s"),GLib.Variant.new_string(self.props.application.current_user_action.props.state.get_string()))
        user_button_activate_action.connect('activate',self.on_activate_users_button)
        user_button_activate_action.connect('change_state',self.on_user_button_action_state_change)
        self.add_action(user_button_activate_action)

        #connection to db
        retry_connection_to_db_action=Gio.SimpleAction.new("retry_connection_to_db",None)
        retry_connection_to_db_action.connect('activate',self.retry_connection_to_db)
        self.add_action(retry_connection_to_db_action)

        #open users page window if open_page variable is set to users_page
        if self.open_page=="users_page":
            self.users_display(None)

    #appearance settings page
    def appearance_display(self,caller_obj):
        self.reload()
        self.current_page='appearance_settings'
        label=Gtk.Label.new("Appearance settings")
        label.set_valign(Gtk.Align.START)
        self.settings_box.append(label)
        self.props.title="settings/appearance"

        #shapes
        shapes_settings_label=Gtk.Label.new("shapes:")
        shapes_settings_label.set_halign(Gtk.Align.START)
        self.settings_box.append(shapes_settings_label)
        shape_buttons_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        self.settings_box.append(shape_buttons_box)
        #default shapes button
        default_shapes_button=Gtk.CheckButton.new_with_label("default")
        default_shapes_button.set_action_name('app.shapes')
        default_shapes_button.set_action_target_value(GLib.Variant.new_string(''))
        shape_buttons_box.append(default_shapes_button)
        #round shapes button
        round_shapes_button=Gtk.CheckButton.new_with_label("round")
        round_shapes_button.set_action_name('app.shapes')
        round_shapes_button.set_action_target_value(GLib.Variant.new_string(self.props.application.css_files_paths['round_css']))
        round_shapes_button.set_group(default_shapes_button)
        shape_buttons_box.append(round_shapes_button)
        
        #add seperator
        seperator=Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.settings_box.append(seperator)

        #colors
        colors_settings_label=Gtk.Label.new("colors:")
        colors_settings_label.set_halign(Gtk.Align.START)
        self.settings_box.append(colors_settings_label)
        colors_buttons_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        self.settings_box.append(colors_buttons_box)
        #default colors button
        default_colors_button=Gtk.CheckButton.new_with_label("default")
        default_colors_button.set_action_name('app.colors')
        default_colors_button.set_action_target_value(GLib.Variant.new_string(''))
        colors_buttons_box.append(default_colors_button)
        #dark mode button
        dark_mode_button=Gtk.CheckButton.new_with_label("dark")
        dark_mode_button.set_action_name('app.colors')
        dark_mode_button.set_action_target_value(GLib.Variant.new_string(self.props.application.css_files_paths['black_shade_css']))
        dark_mode_button.set_group(default_colors_button)
        colors_buttons_box.append(dark_mode_button)
        #colorful mode button
        colors_mode_button=Gtk.CheckButton.new_with_label("colorful")
        colors_mode_button.set_action_name('app.colors')
        colors_mode_button.set_action_target_value(GLib.Variant.new_string(self.props.application.css_files_paths['colorful_css']))
        colors_mode_button.set_group(default_colors_button)
        colors_buttons_box.append(colors_mode_button)
        
        #transparancy slider
        transparancy_slider_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        self.settings_box.append(transparancy_slider_box)

        transparancy_label=Gtk.Label.new('window transparancy:')
        transparancy_label.set_halign(Gtk.Align.START)
        transparancy_slider_box.append(transparancy_label)

        #slider
        transparancy_slider=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,1,0.01)
        transparancy_slider.set_value(1)
        transparancy_slider.set_draw_value(True)
        transparancy_slider.set_hexpand(True)
        transparancy_slider.connect('value_changed',self.update_window_transparancy)
        transparancy_slider_box.append(transparancy_slider)

        #add seperator
        seperator2=Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.settings_box.append(seperator2)

        #button images
        images_settings_label=Gtk.Label.new("button icons:")
        images_settings_label.set_halign(Gtk.Align.START)
        self.settings_box.append(images_settings_label)
        images_buttons_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        self.settings_box.append(images_buttons_box)
        #no images button
        button_images_no_button=Gtk.CheckButton.new_with_label("no")
        button_images_no_button.set_action_name('app.images')
        button_images_no_button.set_action_target_value(GLib.Variant.new_string(''))
        images_buttons_box.append(button_images_no_button)
        #yes images button
        button_images_yes_button=Gtk.CheckButton.new_with_label("yes")
        button_images_yes_button.set_action_name('app.images')
        button_images_yes_button.set_action_target_value(GLib.Variant.new_string(self.props.application.css_files_paths['images_css']))
        button_images_yes_button.set_group(button_images_no_button)
        images_buttons_box.append(button_images_yes_button)

        #add seperator line
        seperator3=Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.settings_box.append(seperator3)

        #custom css
        custom_css_label=Gtk.Label.new("custom css:")
        custom_css_label.set_halign(Gtk.Align.START)
        self.settings_box.append(custom_css_label)
        custom_css_buttons_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        self.settings_box.append(custom_css_buttons_box)
        #no custom css button
        custom_css_no_button=Gtk.CheckButton.new_with_label('no')
        custom_css_no_button.set_action_name('app.custom_css')
        custom_css_no_button.set_action_target_value(GLib.Variant.new_string(''))
        custom_css_buttons_box.append(custom_css_no_button)
        #yes custom css button
        custom_css_yes_button=Gtk.CheckButton.new_with_label('yes')
        custom_css_yes_button.set_group(custom_css_no_button)
        custom_css_yes_button.set_action_name('app.custom_css')
        custom_css_yes_button.set_action_target_value(GLib.Variant.new_string(self.props.application.css_files_paths['custom_css']))
        custom_css_buttons_box.append(custom_css_yes_button)
        
        #font size increase or decrease
        font_size_settings_label=Gtk.Label.new("font size")
        font_size_settings_label.set_halign(Gtk.Align.START)
        self.settings_box.append(font_size_settings_label)
        font_size_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,0)
        self.settings_box.append(font_size_box)
        #font size text box
        font_size_storage=Gtk.EntryBuffer.new(self.get_style_from_css_files('label','font-size'),-1)
        self.font_size_text_box=Gtk.Entry.new_with_buffer(font_size_storage)
        font_size_box.append(self.font_size_text_box)
        #increase font size
        increase_button=Gtk.Button.new_with_label('+')
        increase_button.connect('clicked',self.change_font_size,'increase')
        font_size_box.append(increase_button)
        #decrease font size
        decrease_button=Gtk.Button.new_with_label('-')
        decrease_button.connect('clicked',self.change_font_size,'decrease')
        font_size_box.append(decrease_button)

        #add seperator
        seperator4=Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.settings_box.append(seperator4)

        #general settings checkboxes
        #other styles
        self.styles_css_checkbox=Gtk.CheckButton.new_with_label("remove other styles")
        self.settings_box.append(self.styles_css_checkbox)
        #color styles
        self.white_mode_css_checkbox=Gtk.CheckButton.new_with_label("white mode")
        self.settings_box.append(self.white_mode_css_checkbox)

        #button states
        if self.props.application.style_preference['shapes'] != '':
            self.styles_css_checkbox.props.active=False
        else:
            self.styles_css_checkbox.props.active=True
        if self.props.application.style_preference['colors']!='':
            self.white_mode_css_checkbox.props.active=False
        else:
            self.white_mode_css_checkbox.props.active=True
        #button functions
        self.styles_css_checkbox.connect('toggled',self.change_styles,(self.props.application.css_files_paths["round_css"],"shapes"))
        self.white_mode_css_checkbox.connect('toggled',self.change_styles,(self.props.application.css_files_paths["colorful_css"],"colors"))

    def update_window_transparancy(self,slider):
        transparancy=slider.get_value()
        self.update_style_to_custom_css_file({'window':{'opacity':str(transparancy)}})
        self.props.application.reload_styles()
    def change_font_size(self,caller_obj,mode,increase_by_num=1):
        #get current font size
        current_font_size=self.font_size_text_box.get_buffer().get_text()
        if current_font_size[-2:] != 'px':
            print('please enter font size in pixel(px) unit')
            current_font_size=self.get_style_from_css_files('label','font-size')
        #convert from pixel(px) unit string to integer
        try:
            current_font_size=int(current_font_size[:-2])
        except Exception as e:
            print('Enter valid font size',e)
            current_font_size=self.get_style_from_css_files('label','font-size')

        #increase/decrease the font size
        if mode == "increase":
            current_font_size=current_font_size+increase_by_num
        elif mode == "decrease" and current_font_size-increase_by_num>0:
            current_font_size-=increase_by_num
        elif mode=='decrease' and current_font_size<=0:
            print('negative font size')
        else:
            print('>unknown mode in increase/decrease font size')

        #create the font size css string in pixel(px) unit
        current_font_size=str(current_font_size)+'px'
        
        #set the buffer text in pixel unit
        self.font_size_text_box.get_buffer().set_text(current_font_size,-1)
        #update the font size into a custom css file in pixel units
        self.update_style_to_custom_css_file({'label':{'font-size':current_font_size}})
        
        #reload the styles of the running application
        self.props.application.reload_styles()
    #update font size into a custom css file
    def update_style_to_custom_css_file(self,css_dict):
        try:
            css_file=open(self.props.application.css_files_paths['custom_css'],'r')
            css_file_contents=css_file.read()
            existing_css_dict=self.props.application.read_css(css_file_contents)
            css_file.close()
        except Exception as a:
            print("Error"+a)
            return
        existing_css_dict.update(css_dict)
        #construct the content to write in the css file
        css_label_string=''
        for style_category,styles in existing_css_dict.items():
            #the category{
            css_label_string=f"{css_label_string}\n{style_category}{{"
            for style_name,style_value in styles.items():
                #the css style:value;
                css_label_string=f"{css_label_string}\n\t{str(style_name)}:{str(style_value)};"
            #the }
            css_label_string=f"{css_label_string}\n}}"
        #remove the newline character in empty first line
        css_label_string=css_label_string[1:]

        #open the custom css file to write the new font size
        try:
            css_file=open(self.props.application.css_files_paths['custom_css'],'w')
            #write the css label string constructed above to the custom css file
            css_file.write(css_label_string)
            css_file.close()
        except Exception as a:
            print("Error"+a)
            return

    #get the font size somehow
    def get_style_from_css_files(self,category,style):
        #read css files to get font size
        #custom css file read
        custom_css_file_path=self.props.application.style_preference['custom_css']
        if os.path.isfile(custom_css_file_path):
            custom_css_file_contents=read_file(custom_css_file_path)
            css_dict=self.props.application.read_css(custom_css_file_contents)
            try:
                style=css_dict[category][style]
                print(f'{category}->{style} found in custom css file')
                return style
            except KeyError as e:
                print(f'{category}->{style} in custom css file not found')
        #rounded_edges css file read
        css_file_path=self.props.application.css_files_paths['round_css']
        css_file_contents=read_file(css_file_path)
        css_dict=self.props.application.read_css(css_file_contents)
        try:
            style=css_dict[category][style]
            print(f'{category}->{style} found in rounded_edges file')
            return style
        except KeyError as e:
            print(f'{category}->{style} not found in rounded_edges css file')

        print(f'style {style} from {category} not found while searching custom and rounded_edges css files')
        return ''
    #database settings
    def db_settings_display(self,caller_obj):
        self.reload()
        self.current_page='database_settings'
        self.props.title="settings/database"
        #database directory message display
        db_dir_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        db_dir_box.set_valign(Gtk.Align.START)

        db_dir_label=Gtk.Label.new("Current database name:")
        database_directory_entry_buffer=Gtk.EntryBuffer.new(self.props.application.db_name,-1)
        database_directory_textbox=Gtk.Entry.new_with_buffer(database_directory_entry_buffer)
        database_directory_textbox.set_overwrite_mode(False)
        database_directory_textbox.set_max_length(database_directory_textbox.get_text_length())
        
        db_dir_edit_button=Gtk.Button.new_with_label("Edit")
        db_dir_edit_button.connect('clicked',self.on_db_name_edit_button_click,database_directory_textbox,database_directory_entry_buffer,db_dir_box)

        db_dir_box.append(db_dir_label)
        db_dir_box.append(database_directory_textbox)
        db_dir_box.append(db_dir_edit_button)

        #message text
        if self.props.application.db_cursor!=None:
            connection_status_message="Connection to database available"
        else:
            connection_status_message="Connection to database Unavailable!"
        self.message_label=Gtk.Label.new(connection_status_message)
        #scrolling support for message text
        message_label_scroll=Gtk.ScrolledWindow.new()
        message_label_scroll.set_propagate_natural_height(True)
        message_label_scroll.set_child(self.message_label)

        #reconnect to database button
        connect_to_db_button=Gtk.Button.new_with_label("retry connecting to database")
        connect_to_db_button.set_action_name('win.retry_connection_to_db')

        #add to settings window
        self.settings_box.append(db_dir_box)
        self.settings_box.append(connect_to_db_button)
        self.settings_box.append(message_label_scroll)
    #users settings
    def users_display(self,caller_obj):
        self.reload()
        self.current_page='users_settings'
        self.props.title="settings/users"

        users=self.props.application.users
        #no users message
        if len(self.props.application.users.items()) == 0:
            message=Gtk.Label.new("No users in record!")
            message.set_valign(Gtk.Align.START)
            self.settings_box.append(message)
        #users
        users_buttons_scroller=Gtk.ScrolledWindow.new()
        self.users_buttons_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,4)
        user_operations_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)
        self.messages_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,3)

        self.settings_box.append(users_buttons_scroller)
        self.settings_box.append(user_operations_box)
        self.settings_box.append(self.messages_box)

        users_buttons_scroller.set_propagate_natural_height(True)
        users_buttons_scroller.set_propagate_natural_width(True)
        users_buttons_scroller.set_child(self.users_buttons_box)
        #display the users in users page
        self.update_users_buttons(users_buttons_scroller)

        #operations buttons
        add_user_button=Gtk.Button.new_with_label("Add user")
        remove_user_button=Gtk.Button.new_with_label("Remove current user")
        
        user_operations_box.append(remove_user_button)
        user_operations_box.append(add_user_button)
        
        add_user_button.connect('clicked',self.open_login_page)
        remove_user_button.connect('clicked',self.remove_current_user,users_buttons_scroller)

    #change appearance
    def change_styles(self,check_button,style_providers_list):
        if check_button.props.active == False:
            self.props.application.change_action_state(style_providers_list[1],GLib.Variant.new_string(style_providers_list[0]))
            self.props.application.style_preference[style_providers_list[1]]=style_providers_list[0]
        else:
            self.props.application.change_action_state(style_providers_list[1],GLib.Variant.new_string(''))
            self.props.application.style_preference[style_providers_list[1]]=''
        self.props.application.reload_styles()
    #edit database name
    def on_db_name_edit_button_click(self,caller_obj,db_entry,db_entry_buffer,db_dir_box):
        #change mode allow editing
        db_entry.set_overwrite_mode(True)
        db_entry.set_max_length(0)
        db_dir_box.remove(caller_obj)
        db_entry_contents=db_entry_buffer.get_text()
        #save the changes
        save_button=Gtk.Button.new_with_label("Save")
        db_dir_box.append(save_button)
        #button functions
        save_button.connect('clicked',self.db_name_save_button_click,db_entry_contents,db_dir_box,db_entry,caller_obj)

    #save the new database name
    def db_name_save_button_click(self,caller_obj,db_entry_contents,db_dir_box,db_entry,edit_button):
        self.props.application.db_name=db_entry_contents
        print("saved")
        db_dir_box.remove(caller_obj)
        db_dir_box.append(edit_button)
        db_entry.set_overwrite_mode(True)
        db_entry.set_max_length(0)
    #attempt to connect to database
    def retry_connection_to_db(self,caller_action,param):
        db_connection_status=self.props.application.connect_to_db_server_and_create_db()
        if db_connection_status == True:
            self.message_label.set_text("cursor available!")            

    #on user button action state change
    def on_user_button_action_state_change(*args):
        print("state changed",args)
    #when user button is clicked
    def on_activate_users_button(self,caller_action,parameter):
        caller_action.set_state(parameter)
        self.props.application.current_user_action.set_state(caller_action.props.state)
        self.update_current_user_message(self.messages_box)
    #display the users in users page
    def update_users_buttons(self,scroller):
        #replace current box
        self.users_buttons_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        scroller.set_child(self.users_buttons_box)

        button0=Gtk.CheckButton.new_with_label("No user")
        button0.set_action_name('win.current_user_button')
        button0.set_action_target_value(GLib.Variant.new_string(""))
        self.users_buttons_box.append(button0)
        for user_name in self.props.application.users.keys():
            if user_name=="":
                continue
            button=Gtk.CheckButton.new_with_label(user_name)
            button.set_group(button0)
            button.set_action_name('win.current_user_button')
            button.set_action_target_value(GLib.Variant.new_string(user_name))
            self.users_buttons_box.append(button)
        self.update_current_user_message(self.messages_box)
    #remove current user from users list
    def remove_current_user(self,caller_obj,users_buttons_scroller):
        current_user=self.props.application.current_user_action.props.state.get_string()
        if current_user=="":
            print("No current user")
            old_msg=self.messages_box.get_last_child()
            self.messages_box.remove(old_msg)
            self.messages_box.append(Gtk.Label.new("No current user!"))
            return
        if current_user not in self.props.application.users:
            print("ERROR:Current user not in users dictionary")
            return
        del self.props.application.users[current_user]
        self.props.application.current_user_action.set_state(GLib.Variant.new_string(""))
        self.update_users_buttons(users_buttons_scroller)
    #update current use message in users page
    def update_current_user_message(self,container):
        current_msg=container.get_last_child()
        if current_msg!=None:
            container.remove(current_msg)
        message=self.props.application.current_user_action.props.state.get_string()
        if message != "":
            message="current user: "+message
        label=Gtk.Label.new(message)
        self.messages_box.append(label)
    #add user
    def open_login_page(self,caller_obj):
        self.props.application.open_page(None,login_page)
    #set the state of current_user action to user_name of the given user
    def set_user(self,caller_obj,user_name):
        self.props.application.current_user_action.set_state(GLib.Variant.new_string(user_name))
        self.props.application.current_user=user_name
        self.update_current_user_message(self.messages_box)

    #reload settings window
    def reload(self):
        #relead the settings window by removing and adding new one
        self.current_page=''
        self.settings_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        self.settings_page_scroll.set_child(self.settings_box)
        self.main_box.remove(self.main_box.get_last_child())
        self.main_box.append(self.settings_page_scroll)

#main menu page
class main_menu_page(Gtk.ApplicationWindow):
    message_box=True
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="Chemistry assistant main page")
        self.add_css_class("main_menu")

        main_menu_page_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,0)
        self.set_child(main_menu_page_box)

        #boxes
        #message box
        message_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,0)
        message_box_scroller=Gtk.ScrolledWindow()
        message_box_scroller.set_child(message_box)
        #main menu buttons box
        main_menu_buttons_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        main_menu_buttons_box.set_valign(Gtk.Align.CENTER)
        main_menu_buttons_box.set_halign(Gtk.Align.CENTER)

        #scroll
        #scroll for main menu buttons box
        main_menu_buttons_box_scroller=Gtk.ScrolledWindow()
        main_menu_buttons_box_scroller.set_vexpand(True)
        main_menu_buttons_box_scroller.set_child(main_menu_buttons_box)
        main_menu_buttons_box_scroller.set_propagate_natural_height(True)

        main_menu_page_box.append(message_box_scroller)
        main_menu_page_box.append(main_menu_buttons_box_scroller)

        #message label
        self.message_label=Gtk.Label.new()
        message_box.append(self.message_label)

        #buttons
        reactions_button=Gtk.Button.new_with_label("reactions")
        quiz_button=Gtk.Button.new_with_label("quiz")
        quit_button=Gtk.Button.new_with_label("quit")
        simulator_button=Gtk.Button.new_with_label("search reaction")
        settings_button=Gtk.Button.new()

        #add buttons to box
        main_menu_buttons_box.append(reactions_button)
        main_menu_buttons_box.append(quiz_button)
        main_menu_buttons_box.append(simulator_button)
        main_menu_buttons_box.append(quit_button)
        message_box.append(settings_button)

        #set the default hightlighted widget
        self.set_default_widget(self.get_first_child().get_first_child().get_next_sibling().get_first_child().get_first_child().get_first_child())

        #css
        simulator_button.add_css_class('reactions_button_main_menu')
        reactions_button.add_css_class('reactions_button_main_menu')
        settings_button.add_css_class('icon_button')
        settings_button.add_css_class('settings_button')
        main_menu_buttons_box.add_css_class("main_menu_buttons_box")
        add_css_class_to_children(main_menu_buttons_box,"main_menu_buttons_box")

        #button functions
        reactions_button.set_action_name('app.open_reactions_page')
        quiz_button.set_action_name('app.open_quiz_page')
        quit_button.set_action_name('app.quit')
        simulator_button.connect('clicked',self.props.application.open_page,simulator_page)
        settings_button.connect('clicked',self.props.application.open_page,settings_page)

#login page
class login_page(Gtk.ApplicationWindow):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="user login page")
        header_bar.set_titlebar(header_bar,self,settings=False)

        main_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,self.props.application.monitor_height/3)
        self.set_child(main_box)

        #page contents
        login_message=Gtk.Label.new()    
        entries_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        main_box.append(login_message)
        main_box.append(entries_box)

        #set behaviour
        entries_box.set_valign(Gtk.Align.CENTER)
        entries_box.set_halign(Gtk.Align.CENTER)
    
        login_message.set_markup(f'''
        <span font-size="{int(self.props.application.monitor_width/50)}pt">Login Form</span>''')

        #username and password
        user_name_storage=Gtk.EntryBuffer.new(None,-1)
        password_storage=Gtk.EntryBuffer.new(None,-1)
        
        user_name_entry=Gtk.Entry.new_with_buffer(user_name_storage)
        password_entry=Gtk.Entry.new_with_buffer(password_storage)

        #show password checkbox
        show_password_checkbox=Gtk.CheckButton.new_with_label("show password")
        login_button=Gtk.Button.new_with_label("Login/Add")

        #entry properties
        user_name_entry.set_placeholder_text("user name")
        password_entry.set_visibility(False)
        password_entry.set_placeholder_text("password")
        password_entry.set_invisible_char("#")

        entries_box.append(user_name_entry)
        entries_box.append(password_entry)
        entries_box.append(show_password_checkbox)
        entries_box.append(login_button)

        #spinning animation box
        spnning_animation_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,5)
        self.spinning_animation_message=Gtk.Label.new("Adding user..")
        self.spinning_animation_message.set_visible(False)
        self.spinning_animation=Gtk.Spinner.new()
        spnning_animation_box.append(self.spinning_animation_message)
        spnning_animation_box.append(self.spinning_animation)
        main_box.append(spnning_animation_box)
        #button functions
        login_button.connect('clicked',self.on_login_button_clicked,user_name_storage,password_storage)
        show_password_checkbox.connect('toggled',lambda a:password_entry.set_visibility(show_password_checkbox.props.active)) #show password when checkbox is checked

    def on_login_button_clicked(self,caller_obj,user_name,password):
        #add user to users dict attribute in application class
        user_name=user_name.get_text()
        password=password.get_text()

        self.spinning_animation.start()
        self.spinning_animation_message.set_text("getting users")
        self.spinning_animation.set_visible(True)
        self.spinning_animation_message.set_text("adding user")
        
        #add the user
        self.props.application.users[user_name]=password
        self.props.application.current_user_action.set_state(GLib.Variant.new_string(user_name))
        
        #stop spinning animation
        self.spinning_animation.stop()
        
        #print user added message
        print(self.props.application.users.keys(),"user added, exiting")
        #open the last opened window
        last_opened_window=self.props.application.window_history[-2]
        if last_opened_window == settings_page:
            last_opened_window.open_page="users_page"
        self.props.application.open_page(None,last_opened_window)

#quiz page
class quiz_main_page(Gtk.ApplicationWindow):
    message_box=True
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="Quiz main page")
        header_bar.set_titlebar(header_bar,self)

        #main box
        quiz_main_page_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,0)
        self.set_child(quiz_main_page_box)
        
        #message box
        self.message_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        #message box message
        self.message_label=Gtk.Label.new()
        self.message_box.append(self.message_label)
        #scroll
        message_box_scroll=Gtk.ScrolledWindow.new()
        message_box_scroll.set_child(self.message_box)

        #buttons
        start_quiz_button=Gtk.Button.new_with_label("Start quiz")
        #button properties
        start_quiz_button.set_vexpand(True)
        start_quiz_button.add_css_class("start_quiz_button")

        #button function
        #start the quiz
        start_quiz_button.set_action_name('app.open_quiz')

        #add to main page
        quiz_main_page_box.append(message_box_scroll)
        quiz_main_page_box.append(start_quiz_button)


#Reactions page
class reactions_display_page(Gtk.ApplicationWindow):
    message_box=True
    message_label=Gtk.Label.new()
    pull_data_from_reactions_table=False
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="Reactions")
        #create a message label with existing text
        self.message_label=Gtk.Label.new(self.message_label.get_label())

        ##db
        #connect to database server, create database and set it as current database
        connect_to_db_server_and_create_db_return=self.props.application.connect_to_db_server_and_create_db()
        #create reactions table
        create_reactions_table_return=False
        if connect_to_db_server_and_create_db_return==True:
            #creating the table
            create_reactions_table_return=self.props.application.create_reactions_table(self.props.application.db_cursor)
            #if reactions table connection exists, then only take data from there
            if create_reactions_table_return==True:
                self.pull_data_from_reactions_table=True
            else:
                #display error and exit function with return value as false
                if self.props.application.window_history[-1].message_box==True:
                    self.props.application.props.active_window.message_label.set_text("Error: "+str(create_reactions_table_return))
                print("could not create reactions table")

        ##title
        title_message="Reactions"
        #user
        if self.props.application.current_user_action.props.state.get_string()!="":
            title_message=title_message+" (user:"+self.props.application.current_user_action.props.state.get_string()+")"
        #database
        if self.pull_data_from_reactions_table == False:
            title_message=title_message+"(no db connection)"
        elif self.props.application.database_object.is_connected():
            title_message=title_message[:-1]+",database:"+self.props.application.db_name+")"
        self.set_title(title_message)
        #titlebar
        header_bar.set_titlebar(header_bar,self)

        ##layout
        #scroll
        reactions_page_box_scroller=Gtk.ScrolledWindow.new()
        self.set_child(reactions_page_box_scroller)

        message_box_scroll=Gtk.ScrolledWindow.new()

        #boxes
        reactions_page_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        reactions_page_bottom_panel_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,10)

        #add scroll support
        reactions_page_box_scroller.set_child(reactions_page_box)
        message_box_scroll.set_child(self.message_label)

        #add to page
        reactions_page_box.append(message_box_scroll)
        reactions_page_box.append(reactions_page_bottom_panel_box)

        #box properties
        reactions_page_box.set_halign(Gtk.Align.FILL)

        reactions_page_bottom_panel_box.set_valign(Gtk.Align.END)
        reactions_page_bottom_panel_box.set_halign(Gtk.Align.CENTER)

        ##reactions list
        #list storage
        reactions_list=Gio.ListStore.new(reaction_info)
        self.reactions_list_single_selection=Gtk.SingleSelection.new(reactions_list)

        #name column
        name_column_signal_factory=Gtk.SignalListItemFactory.new()
        name_column=Gtk.ColumnViewColumn.new("name",name_column_signal_factory)
        #reaction column
        reaction_column_signal_list_item_factory=Gtk.SignalListItemFactory.new()
        reaction_column=Gtk.ColumnViewColumn.new("reaction",reaction_column_signal_list_item_factory)
        #extra info column
        extra_info_column_signal_factory=Gtk.SignalListItemFactory.new()
        extra_info_column=Gtk.ColumnViewColumn.new("extra_info",extra_info_column_signal_factory)
        extra_info_column.props.resizable=True

        #column properties
        #for column headers to take up the horizontal space
        name_column.set_expand(True)
        reaction_column.set_expand(True)
        extra_info_column.set_expand(True)

        #display items
        name_column_signal_factory.connect("setup",self.add_label_to_column)
        reaction_column_signal_list_item_factory.connect("setup",self.add_reaction)
        extra_info_column_signal_factory.connect("setup",self.add_label_to_column)

        name_column_signal_factory.connect("bind",self.set_column_cell_label,1)
        reaction_column_signal_list_item_factory.connect("bind",self.display_reaction)
        extra_info_column_signal_factory.connect("bind",self.set_column_cell_label,3)

        name_column_signal_factory.connect("unbind",self.remove_element_from_column)
        reaction_column_signal_list_item_factory.connect("unbind",self.remove_element_from_column,True)
        extra_info_column_signal_factory.connect("unbind",self.remove_element_from_column)

        #create column view
        self.reactions_column_manager=Gtk.ColumnView.new(self.reactions_list_single_selection)
        self.reactions_column_manager.append_column(name_column)
        self.reactions_column_manager.append_column(reaction_column)
        self.reactions_column_manager.append_column(extra_info_column)
        self.reactions_column_manager.set_vexpand(True)

        ##bottom panel
        refresh_button=Gtk.Button.new()
        # reactions_db_import_button=Gtk.Button.new_with_label("Import")
        # reactions_db_export_button=Gtk.Button.new_with_label("Export")
        reactions_db_add_button=Gtk.Button.new_with_label("Add")
        reaction_edit_button=Gtk.Button.new_with_label("edit")
        reaction_remove_button=Gtk.Button.new_with_label("delete")
        #styling
        refresh_button.add_css_class('icon_button')
        refresh_button.add_css_class('refresh_button')

        #add to box
        reactions_page_bottom_panel_box.append(refresh_button)
        reactions_page_box.prepend(self.reactions_column_manager)
        if self.pull_data_from_reactions_table:
            #fetch data from database and add it to reactions list
            self.add_reactions_data_to_list()

            reactions_page_bottom_panel_box.append(reaction_edit_button)
            reactions_page_bottom_panel_box.append(reaction_remove_button)
            reactions_page_bottom_panel_box.append(reactions_db_add_button)
            #reactions_page_bottom_panel_box.append(reactions_db_import_button)
            #reactions_page_bottom_panel_box.append(reactions_db_export_button)
        #if there is not database connection, display message
        elif self.pull_data_from_reactions_table == False:
            no_connection_message=Gtk.Label.new("No database connection!")
            no_connection_message.set_vexpand(True)
            self.reactions_column_manager.set_vexpand(False)
            reactions_page_box.insert_child_after(no_connection_message,reactions_page_box.get_first_child())
        #button functions
        refresh_button.connect('clicked',self.refresh_reactions_list)
        reaction_edit_button.connect('clicked',self.edit_selected_reaction)
        reaction_remove_button.connect('clicked',self.remove_selected_reaction)
        reactions_db_add_button.connect('clicked',self.add_reaction_to_db)
        #edit row function
        self.reactions_column_manager.connect('activate',self.edit_row)
    def edit_selected_reaction(self,caller_obj):
        #open edit row page if a row is selected
        selected_row_number=self.reactions_list_single_selection.props.selected
        if type(selected_row_number)==int:
            self.edit_row(None,self.reactions_list_single_selection.props.selected)
        else:
            print(f"No row selected(selected row:{selected_row_number})")
    #remove selected reaction from reactions list
    def remove_selected_reaction(self,caller_obj):
        selected_row_number=self.reactions_list_single_selection.props.selected
        if type(selected_row_number)==int:
            #remove reaction from reactions database
            try:
                delete_reaction_command=f"delete from reactions where name='{self.reactions_list_single_selection.get_model()[selected_row_number].name}'"
                print(delete_reaction_command)
                self.props.application.db_cursor.execute(delete_reaction_command)
                self.props.application.database_object.commit()
            except mysql.connector.Error as err:
                print("error while deleting record from database:",err)
            self.reactions_list_single_selection.get_model().remove(selected_row_number)
        else:
            print(f"No row selected(selected row:{selected_row_number})")
            
    def edit_row(self,caller_obj,row_position):
        reactions_list=self.reactions_list_single_selection.get_model()
        reaction=reactions_list[row_position]
        #reaction details as a list
        reaction_details=[
            reaction.name,
            reaction.reactants,
            reaction.products,
            reaction.extra_info
        ]
        reaction_edit_page=add_reaction_to_db_page
        #set reaction information list
        reaction_edit_page.reaction_information=reaction_details
        self.props.application.open_page(None,reaction_edit_page)
    def refresh_reactions_list(self,caller_obj):
        print("refreshing page")
        self.props.application.open_page(None,reactions_display_page)

    #prepare the column
    def add_label_to_column(self,caller_factory,column_cell):
        column_cell_scroll=Gtk.ScrolledWindow.new()
        column_cell_scroll.set_child(Gtk.Label.new())
        column_cell_scroll.set_propagate_natural_width(True)

        column_cell.set_child(column_cell_scroll)
    def add_reaction(self,caller_factory,column_cell):
        reaction_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,2)

        #reactants
        reactants_scroll=Gtk.ScrolledWindow.new()
        reactants_scroll.set_propagate_natural_width(True)
        reactants_scroll.set_child(Gtk.Label.new())

        #arrow
        arrow=Gtk.Label.new()
        arrow.set_text("----->")
        
        #products
        products_scroll=Gtk.ScrolledWindow.new()
        products_scroll.set_propagate_natural_width(True)
        products_scroll.set_child(Gtk.Label.new())

        #add to reaction box
        reaction_box.append(reactants_scroll)
        reaction_box.append(arrow)
        reaction_box.append(products_scroll)

        #add to column
        column_cell.set_child(reaction_box)
    #display on column
    def display_reaction(self,caller_factory,column_cell):
        #set the text for the column
        reaction=self.reactions_list_single_selection.get_model()[column_cell.get_position()]
        #get products label from the column cell and set text
        column_cell.get_child().get_first_child().get_child().get_child().set_text(reaction.reactants)
        #get the reactants label from the column cell and set text
        column_cell.get_child().get_first_child().get_next_sibling().get_next_sibling().get_child().get_child().set_text(reaction.products)
    def set_column_cell_label(self,caller_factory,column_cell,column_number):
        #cell position
        cell_position=column_cell.get_position()
        #reactions list
        reactions_list=self.reactions_list_single_selection.get_model()
        #reaction object
        reaction_details=reactions_list[cell_position]
        column_num_to_column_val_dict={
            1:reaction_details.name,
            3:reaction_details.extra_info
        }
        label_text=column_num_to_column_val_dict[column_number]
        #set entry value
        column_cell.get_child().props.child.get_child().set_text(label_text)
    #remove data from column
    def remove_element_from_column(self,caller_factory,column_cell,reaction_column=False):
        if reaction_column==False:
            column_cell.get_child().get_child().get_child().set_text("")
        if reaction_column==True:
            column_cell.get_child().get_first_child().get_child().get_child().set_text("")
            column_cell.get_child().get_last_child().get_child().get_child().set_text("")

    #add reaction to reactions table
    def add_reaction_to_db(self,caller_obj):
        add_reaction_to_db_page.reaction_information=["","","",""]
        self.props.application.open_page(None,add_reaction_to_db_page)
    
    #get reactions from reactions table and add them to list
    def add_reactions_data_to_list(self):
        get_data_from_reactions_table_command="select * from reactions"
        #get reactions data from database
        self.props.application.db_cursor.execute(get_data_from_reactions_table_command)
        reactions_list=self.props.application.db_cursor.fetchall()
        #reaction list to gobject, append to list
        for reaction in reactions_list:
            reaction_gobject=reaction_info(reaction[0],reaction[1],reaction[2],reaction[3])
            self.reactions_list_single_selection.get_model().append(reaction_gobject)


#add reactions to table page
class add_reaction_to_db_page(Gtk.ApplicationWindow):
    mode="add"
    reaction_information=["","","",""]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="add/edit reaction")
        header_bar.set_titlebar(header_bar,self)
        #set window mode
        for detail in self.reaction_information:
            if detail != "":
                self.mode="edit"

        main_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        self.set_child(main_box)

        #labels
        name_label=Gtk.Label.new("name:")
        reactants_label=Gtk.Label.new("reactants:")
        products_label=Gtk.Label.new("products:")
        extra_info_label=Gtk.Label.new("extra information:")
        #label behaviour
        name_entry_buffer=Gtk.EntryBuffer.new(self.reaction_information[0],-1)
        reactants_entry_buffer=Gtk.EntryBuffer.new(self.reaction_information[1],-1)
        products_entry_buffer=Gtk.EntryBuffer.new(self.reaction_information[2],-1)
        extra_info_entry_buffer=Gtk.EntryBuffer.new(self.reaction_information[3],-1)
        
        name_entry=Gtk.Entry.new_with_buffer(name_entry_buffer)
        reactant_entry=Gtk.Entry.new_with_buffer(reactants_entry_buffer)
        product_entry=Gtk.Entry.new_with_buffer(products_entry_buffer)
        extra_info_entry=Gtk.Entry.new_with_buffer(extra_info_entry_buffer)

        name_entry.set_placeholder_text("name")
        reactant_entry.set_placeholder_text("reactants")
        product_entry.set_placeholder_text("products")
        extra_info_entry.set_placeholder_text("extra info")

        add_button=Gtk.Button.new_with_label("add/edit")
        add_button.set_halign(Gtk.Align.CENTER)

        #add to main box
        main_box.append(name_label)
        main_box.append(name_entry)
        main_box.append(reactants_label)
        main_box.append(reactant_entry)
        main_box.append(products_label)
        main_box.append(product_entry)
        main_box.append(extra_info_label)
        main_box.append(extra_info_entry)
        main_box.append(add_button)
        
        #reaction_details_buffers=(reactants_entry_buffer,name_entry_buffer,products_entry_buffer,extra_info_entry_buffer)
        add_button.connect('clicked',self.add_reaction_to_db,(name_entry_buffer,reactants_entry_buffer,products_entry_buffer,extra_info_entry_buffer))
    def add_reaction_to_db(self,caller_obj,reaction_details_buffers):
        #columns
        columns=self.props.application.reactions_table_columns
        #construct command for database
        if self.mode=="add":
            columns_str=""
            for column in columns:
                columns_str = columns_str + column + ","
            columns_str=columns_str[:-1]
            #values
            values_str=""
            for i in reaction_details_buffers:
                i=i.get_text()

                #if the string has a space or tab in the end, remove it
                if i != "":
                    while i[-1] == " " or i[-1] == '\t' :
                        i=i[:-1]

                values_str=values_str+"'"+i+"',"
            values_str=values_str[:-1]
            #command insert details in table
            reactions_table_command_string=f"insert into reactions ({columns_str}) values({values_str});"
        if self.mode=="edit":
            #edited info
            name=reaction_details_buffers[0].get_text()
            reactants=reaction_details_buffers[1].get_text()
            products=reaction_details_buffers[2].get_text()
            extra_info=reaction_details_buffers[3].get_text()
            edited_reaction_information=[name,reactants,products,extra_info]

            #db query string construct
            reactions_table_command_string="update reactions set"
            reaction_not_edited=True
            for i in range(len(edited_reaction_information)):

                #if the string has a space or tab in the end, remove it
                if edited_reaction_information[i] != "":
                    while edited_reaction_information[i][-1] == " " or edited_reaction_information[i][-1] == '\t' :
                        edited_reaction_information[i]=edited_reaction_information[i][:-1]
                
                #if reaction is edited set this variable to false
                if self.reaction_information[i] != edited_reaction_information[i]:
                    reaction_not_edited=False

                #string for the edited information in sql syntax
                reactions_table_command_string=reactions_table_command_string+f" {columns[i]}='{edited_reaction_information[i]}',"

            #exit if reaction is unedited
            if reaction_not_edited==True:
                #open previous window
                previous_window=self.props.application.window_history[-2]
                self.props.application.open_page(None,previous_window)
                return

            #identify the reaction with name
            reactions_table_command_string=reactions_table_command_string[:-1]+f" where name='{self.reaction_information[0]}';"
        #send command to database
        print(reactions_table_command_string)
        try:
            self.props.application.db_cursor.execute(reactions_table_command_string)
            self.props.application.database_object.commit()
        except mysql.connector.Error as err:
                print(f"Error while {self.mode}ing reactions details to table:\n",err)
        
        #open previous window
        previous_window=self.props.application.window_history[-2]
        self.props.application.open_page(None,previous_window)

class simulator_page(Gtk.ApplicationWindow):
    message_box=True
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs,title="simulate")
        header_bar.set_titlebar(header_bar,self)

        main_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,5)
        self.set_child(main_box)

        #reactants box
        reactants_box_scroll=Gtk.ScrolledWindow.new()
        reactants_box_scroll.set_propagate_natural_height(True)
        self.reactants_box=Gtk.Box.new(Gtk.Orientation.VERTICAL,5)
        reactants_box_scroll.set_child(self.reactants_box)
        main_box.append(reactants_box_scroll)

        self.reactants_count = 0
        #add the first entry
        self.add_reactant_entry(None)
        
        #add reactants button
        add_reactants_button=Gtk.Button.new_with_label("+")
        add_reactants_button.set_halign(Gtk.Align.CENTER)
        add_reactants_button.connect('clicked',self.add_reactant_entry)
        main_box.append(add_reactants_button)
        #search button
        search_button=Gtk.Button.new_with_label("search")
        search_button.set_halign(Gtk.Align.CENTER)
        search_button.set_valign(Gtk.Align.END)
        search_button.set_vexpand(True)
        search_button.connect('clicked',self.display_products)

        main_box.append(search_button)

        #message box
        self.message_label=Gtk.Label.new()
        self.message_label.set_valign(Gtk.Align.END)
        main_box.append(self.message_label)
    
    def add_reactant_entry(self,caller_obj):
        self.reactants_count+=1
        reactant_box=Gtk.Box.new(Gtk.Orientation.HORIZONTAL,0)

        label=Gtk.Label.new("Reactant "+str(self.reactants_count)+": ")
        reactant_box.append(label)

        buffer=Gtk.EntryBuffer.new(None,-1)
        entry=Gtk.Entry.new_with_buffer(buffer)
        entry.set_hexpand(True)
        reactant_box.append(entry)

        self.reactants_box.append(reactant_box)

    def search_reaction(self):
        #get text from reactants box
        reactants=[]

        reactant_box=self.reactants_box.get_first_child()
        while reactant_box != None:
            entry=reactant_box.get_last_child()
            reactant=entry.get_buffer().get_text()

            #add reactant to list if its not empty
            if reactant != "" :
                reactants.append(reactant)

            #get next reactant entry
            reactant_box=reactant_box.get_next_sibling()

        #join reactants into string seperated by +
        reactants_string="+".join(reactants)

        #database cursor and reactions table
        if self.get_database_cursor() == False or self.search_for_reactions_table() == False:
            return False
        
        #find the reaction
        search_command=f"select * from reactions where reactants='{reactants_string}'"
        self.props.application.db_cursor.execute(search_command)
        result=self.props.application.db_cursor.fetchone()
        
        if result == None:
            self.display(f'{reactants_string} reaction not found')
            return None
        result_reaction_string=result[1]
        if result_reaction_string == reactants_string:
            self.display("reaction found")
        else:
            self.display("???unknown case")
            return False
        return result

    #display the products on screen
    def display_products(self,caller_obj):
        result=self.search_reaction()

        #exit if reaction not found
        if result==None or result==False:
            return

        products_string=result[3]
        products_label=Gtk.Label.new(products_string)

        self.get_child().insert_child_after(products_label,self.get_child().get_first_child().get_next_sibling())

    #look for reactions table in database
    def search_for_reactions_table(self):
        #search for database
        db_search_sql_command=f"select SCHEMA_NAME from INFORMATION_SCHEMA.SCHEMATA where SCHEMA_NAME='{self.props.application.db_name}'"
        self.props.application.db_cursor.execute(db_search_sql_command)
        db_search_result=self.props.application.db_cursor.fetchone()[0]
        #exit function if database not found
        if self.search_result_error_handle(db_search_result,self.props.application.db_name,"database") != True:
            return False
        
        self.props.application.db_cursor.execute(f"use {self.props.application.db_name}")
        
        #search for table
        table_name='reactions'
        reactions_table_search_command=f"select TABLE_NAME from INFORMATION_SCHEMA.TABLES where TABLE_SCHEMA = '{self.props.application.db_name}' and TABLE_NAME='{table_name}';"
        self.props.application.db_cursor.execute(reactions_table_search_command)
        table_search_result=self.props.application.db_cursor.fetchone()[0]
        #exit function if table not found
        if self.search_result_error_handle(table_search_result,table_name,"table") != True:
            return False
        return True

    #display message according to search result
    def search_result_error_handle(self,search_result,search_item,category=""):
        if search_result == None :
            message=f"{search_item} {category} not found"
            self.display(message)
            return False
        elif search_result == search_item:
            message=f"{search_item} {category} found"
            self.display(message)
        else:
            message="??unknown case"
            print(search_item)
            print(search_results)
            self.display(message)
            return False
        return True
    #display a message in console and on gtk window
    def display(self,message):
        print(message)
        self.message_label.set_text(message)

    #get database cursot
    def get_database_cursor(self):
        #connect to server
        server_connect_return=self.props.application.connect_to_db_server()
        #display error on screen if connection fails
        if server_connect_return!=True:
            self.message_label.set_text(str(server_connect_return))
            return False

        #get cursor
        get_cursor_return=self.props.application.get_cursor_from_db_connection(self.props.application.database_object)
        #display error if getting cursor fails
        if get_cursor_return != True:
            self.message_label.set_text(str(get_cursor_return))
            return False
        return True