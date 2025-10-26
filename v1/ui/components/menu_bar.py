from PyQt6 import QtWidgets, QtGui, QtCore

class MenuBar:
    """Setup menubar and actions"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.menubar = None
        self.actions = {}
        self.menus = {}
    
    def setup_menubar(self):
        """Create and setup menubar"""
        # Create menubar
        self.menubar = QtWidgets.QMenuBar(parent=self.main_window)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
        self.menubar.setObjectName("menubar")
        
        # Create menus
        self._create_menus()
        
        # Create actions
        self._create_actions()
        
        # Add actions to menus
        self._setup_menu_actions()
        
        # Set menubar
        self.main_window.setMenuBar(self.menubar)
        
        return self.menubar
    
    def _create_menus(self):
        """Create menu items"""
        menu_data = [
            ("menuFile", "File"),
            ("menuView", "View"),
            ("menuInsert", "Insert"),
            ("menuTools", "Tools"),
            ("menuWindows", "Windows")
        ]
        
        for obj_name, title in menu_data:
            menu = QtWidgets.QMenu(parent=self.menubar)
            menu.setObjectName(obj_name)
            menu.setTitle(title)
            self.menus[obj_name] = menu
            self.menubar.addAction(menu.menuAction())
    
    def _create_actions(self):
        """Create all actions"""
        actions_data = [
            # (object_name, text, icon_theme, shortcut)
            ("actionRefresh", "Refresh", "applications-engineering", "F5"),
            ("actionClose", "Close", None, "Ctrl+W"),
            ("actionExit", "Exit", None, "Ctrl+Q"),
            ("actionSymbols", "Symbols", None, None),
            ("actionMarketWatch", "Market Watch", None, None),
            ("actionIndicator", "Indicator", None, None),
            ("actionToolbox", "Toolbox", None, None),
            ("actionFullScreen", "Full Screen", None, "F11"),
            ("actionIndicator2", "Indicator", None, None),
            ("actionScript", "Script", None, None),
            ("actionOptions", "Options", None, "Ctrl+,"),
        ]
        
        for data in actions_data:
            obj_name = data[0]
            text = data[1]
            icon_theme = data[2] if len(data) > 2 else None
            shortcut = data[3] if len(data) > 3 else None
            
            action = QtGui.QAction(parent=self.main_window)
            action.setObjectName(obj_name)
            action.setText(text)
            
            if icon_theme:
                icon = QtGui.QIcon.fromTheme(icon_theme)
                action.setIcon(icon)
            
            if shortcut:
                action.setShortcut(shortcut)
            
            self.actions[obj_name] = action
    
    def _setup_menu_actions(self):
        """Add actions to menus"""
        # File menu
        self.menus["menuFile"].addAction(self.actions["actionRefresh"])
        self.menus["menuFile"].addAction(self.actions["actionClose"])
        self.menus["menuFile"].addSeparator()
        self.menus["menuFile"].addAction(self.actions["actionExit"])
        
        # View menu
        self.menus["menuView"].addAction(self.actions["actionSymbols"])
        self.menus["menuView"].addSeparator()
        self.menus["menuView"].addAction(self.actions["actionMarketWatch"])
        self.menus["menuView"].addAction(self.actions["actionIndicator"])
        self.menus["menuView"].addAction(self.actions["actionToolbox"])
        self.menus["menuView"].addSeparator()
        self.menus["menuView"].addAction(self.actions["actionFullScreen"])
        
        # Insert menu
        self.menus["menuInsert"].addAction(self.actions["actionIndicator2"])
        self.menus["menuInsert"].addAction(self.actions["actionScript"])
        
        # Tools menu
        self.menus["menuTools"].addAction(self.actions["actionOptions"])
    
    def connect_actions(self, callbacks):
        """Connect actions to callback functions
        
        Args:
            callbacks: dict with action names as keys and functions as values
            Example: {"actionExit": self.close, "actionRefresh": self.refresh}
        """
        for action_name, callback in callbacks.items():
            if action_name in self.actions:
                self.actions[action_name].triggered.connect(callback)
    
    def get_action(self, action_name):
        """Get action by name"""
        return self.actions.get(action_name)
    
    def get_menu(self, menu_name):
        """Get menu by name"""
        return self.menus.get(menu_name)