# Object-Oriented Programming (OOP) in This Codebase

This guide explains all OOP concepts used in your Discord bot codebase with real examples.

---

## 📚 Table of Contents

1. [Classes and Objects](#1-classes-and-objects)
2. [The `__init__` Method (Constructor)](#2-the-__init__-method-constructor)
3. [Instance Methods](#3-instance-methods)
4. [Static Methods](#4-static-methods)
5. [Inheritance](#5-inheritance)
6. [Method Overriding](#6-method-overriding)
7. [The `super()` Function](#7-the-super-function)
8. [Class Attributes vs Instance Attributes](#8-class-attributes-vs-instance-attributes)
9. [Composition](#9-composition)
10. [Abstract Base Classes](#10-abstract-base-classes)
11. [Special Methods (Dunder Methods)](#11-special-methods-dunder-methods)
12. [Decorators in OOP](#12-decorators-in-oop)

---

## 1. Classes and Objects

### What is a Class?
A **class** is a blueprint for creating objects. It defines attributes (data) and methods (functions) that objects of that class will have.

### What is an Object?
An **object** is an instance of a class. It's a concrete realization of the class blueprint.

### Example from Your Codebase:

```python
# models/user_model.py
class UserModel:
    """Database operations for users table"""
    pass

# Creating an object (instance)
# This happens when you call: UserModel.get_user_by_discord_id(...)
```

**Real Usage:**
```python
# In cogs/leave_management.py
from models.user_model import UserModel

# UserModel is the class
# We call its static methods without creating an object
user = await UserModel.get_user_by_discord_id(interaction.user.id)
```

---

## 2. The `__init__` Method (Constructor)

### Purpose
`__init__` is a special method called automatically when you create an object. It initializes the object's attributes.

### Example from Your Codebase:

```python
# main.py
class CustomBot(commands.Bot):
    """Main bot class"""
    
    def __init__(self):
        # Initialize parent class first
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        
        # Call parent class constructor
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=Config.APPLICATION_ID
        )
```

**Another Example:**
```python
# cogs/leave_management.py
class LeaveManagement(commands.Cog):
    """Leave management commands"""
    
    def __init__(self, bot):
        self.bot = bot  # Store the bot instance as an attribute
```

**Key Points:**
- `__init__` is called automatically when you create an object
- `self` refers to the instance being created
- You can set instance attributes (like `self.bot`)

---

## 3. Instance Methods

### What are Instance Methods?
Methods that belong to an object instance. They can access and modify instance attributes.

### Example from Your Codebase:

```python
# cogs/leave_management.py
class LeaveManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Instance attribute
    
    # Instance method - uses 'self' to access instance attributes
    async def leave_request(self, interaction: discord.Interaction):
        """Start the leave request process"""
        await interaction.response.defer(ephemeral=True)
        # Can access self.bot here if needed
```

**Key Points:**
- First parameter is always `self`
- Can access instance attributes via `self.attribute_name`
- Called on an object: `object.method_name()`

---

## 4. Static Methods

### What are Static Methods?
Methods that belong to the class, not the instance. They don't need `self` and can't access instance attributes.

### Example from Your Codebase:

```python
# models/user_model.py
class UserModel:
    """Database operations for users table"""
    
    @staticmethod
    async def user_registration(discord_id: int, name: str, department: str = None):
        """Register a new user with all details and permissions"""
        # No 'self' parameter - this is a static method
        async with db.pool.acquire() as conn:
            # ... database operations
            return user_id
```

**Usage:**
```python
# Called directly on the class, not an instance
user_id = await UserModel.user_registration(
    discord_id=123456,
    name="John Doe",
    department="IT"
)
```

**Why Use Static Methods?**
- When the method doesn't need instance data
- For utility functions related to the class
- Common in your Model classes (UserModel, LeaveRequestModel, etc.)

**Key Points:**
- Decorated with `@staticmethod`
- No `self` parameter
- Called on the class: `ClassName.method_name()`
- Cannot access instance attributes

---

## 5. Inheritance

### What is Inheritance?
Inheritance allows a class to inherit attributes and methods from another class (parent/superclass).

### Example from Your Codebase:

```python
# main.py
class CustomBot(commands.Bot):  # CustomBot inherits from commands.Bot
    """Main bot class"""
    
    def __init__(self):
        # Call parent class constructor
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=Config.APPLICATION_ID
        )
    
    # Override parent's method
    async def setup_hook(self):
        """Load cogs and sync commands when bot starts"""
        # Custom implementation
        await db.connect()
        await self.load_extension('cogs.user_management')
        # ... more code
```

**Another Example:**
```python
# cogs/leave_management.py
class LeaveManagement(commands.Cog):  # Inherits from commands.Cog
    """Leave management commands"""
    pass
```

**More Examples:**
```python
# views/leave_management_views.py
class LeaveTypeSelectView(discord.ui.View):  # Inherits from discord.ui.View
    """Select leave type"""
    def __init__(self):
        super().__init__(timeout=180)  # Call parent constructor
        self.selected_leave_type = None

class PaidLeaveModal(discord.ui.Modal):  # Inherits from discord.ui.Modal
    """Modal for paid leave request"""
    # Inherits all Modal functionality from discord.py
```

**Key Points:**
- Child class gets all methods and attributes from parent
- Can override parent methods
- Use `super()` to call parent methods
- Promotes code reuse

---

## 6. Method Overriding

### What is Method Overriding?
When a child class provides its own implementation of a method that exists in the parent class.

### Example from Your Codebase:

```python
# main.py
class CustomBot(commands.Bot):
    # Override parent's setup_hook method
    async def setup_hook(self):
        """Load cogs and sync commands when bot starts"""
        # Custom implementation different from parent
        await db.connect()
        await self.execute_sql_file('databases/schema.sql')
        # ... custom code
    
    # Override parent's on_ready method
    async def on_ready(self):
        """Called when bot connects to Discord"""
        logger.info(f'Logged in as {self.user}')
        # Custom implementation
    
    # Override parent's close method
    async def close(self):
        """Clean up when bot shuts down"""
        await db.disconnect()
        await super().close()  # Call parent's close too
```

**Key Points:**
- Same method name as parent
- Different implementation
- Can still call parent method with `super()`

---

## 7. The `super()` Function

### Purpose
`super()` gives you access to the parent class methods and attributes.

### Example from Your Codebase:

```python
# main.py
class CustomBot(commands.Bot):
    def __init__(self):
        # Call parent class (commands.Bot) __init__
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=Config.APPLICATION_ID
        )
    
    async def close(self):
        await db.disconnect()
        await super().close()  # Call parent's close method
```

**Another Example:**
```python
# views/leave_management_views.py
class LeaveTypeSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)  # Initialize parent View with timeout
        self.selected_leave_type = None
```

**Key Points:**
- `super()` returns a proxy object of the parent class
- Used to call parent methods
- Essential for proper inheritance

---

## 8. Class Attributes vs Instance Attributes

### Class Attributes
Belong to the class itself, shared by all instances.

### Instance Attributes
Belong to a specific instance, unique to each object.

### Example from Your Codebase:

```python
# cogs/leave_management.py
class LeaveManagement(commands.Cog):
    # This is a class-level docstring (shared by all instances)
    """Leave management commands"""
    
    def __init__(self, bot):
        # Instance attribute - unique to each LeaveManagement object
        self.bot = bot
```

**Another Example:**
```python
# views/leave_management_views.py
class PaidLeaveModal(discord.ui.Modal, title="Paid Leave Request"):
    """Modal for paid leave request"""
    
    # Class attributes (shared by all instances)
    start_date = discord.ui.TextInput(...)
    end_date = discord.ui.TextInput(...)
    reason = discord.ui.TextInput(...)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Access class attributes via self
        start = datetime.strptime(self.start_date.value, "%d/%m/%Y")
        # self.start_date.value is an instance-specific value
```

**Key Points:**
- Class attributes: defined at class level, shared
- Instance attributes: defined in `__init__`, unique per object
- Access both via `self.attribute_name`

---

## 9. Composition

### What is Composition?
Composition is when a class contains objects of other classes as attributes (has-a relationship).

### Example from Your Codebase:

```python
# cogs/leave_management.py
class LeaveManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Composition: LeaveManagement HAS-A bot
    
    async def leave_request(self, interaction: discord.Interaction):
        # Using UserModel (composition)
        user = await UserModel.get_user_by_discord_id(interaction.user.id)
        
        # Using LeaveRequestModel (composition)
        leave_requests = await LeaveRequestModel.get_user_leave_requests(...)
        
        # Using LeaveTypeSelectView (composition)
        view = LeaveTypeSelectView()
```

**Another Example:**
```python
# main.py
class CustomBot(commands.Bot):
    async def setup_hook(self):
        # Composition: Bot uses database object
        await db.connect()
        
        # Composition: Bot uses UserModel
        user_data = await UserModel.get_user_by_discord_id(...)
```

**Key Points:**
- "Has-a" relationship (vs "Is-a" in inheritance)
- Objects contain other objects
- More flexible than inheritance in some cases

---

## 10. Abstract Base Classes

### What are Abstract Base Classes?
Classes that define a structure but don't provide full implementation. Child classes must implement certain methods.

### Example from Your Codebase:

```python
# Your classes inherit from Discord.py abstract classes:

# discord.ui.View is an abstract base class
class LeaveTypeSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    # You implement methods that View expects
    @discord.ui.select(...)
    async def leave_type_select(self, interaction, select):
        # Your implementation
        pass

# discord.ui.Modal is an abstract base class
class PaidLeaveModal(discord.ui.Modal):
    # Modal expects on_submit method
    async def on_submit(self, interaction: discord.Interaction):
        # Your implementation
        pass

# commands.Cog is an abstract base class
class LeaveManagement(commands.Cog):
    # Cog expects certain structure
    def __init__(self, bot):
        self.bot = bot
```

**Key Points:**
- Define structure/interface
- Child classes must implement required methods
- Enforces consistency

---

## 11. Special Methods (Dunder Methods)

### What are Dunder Methods?
Methods with double underscores (like `__init__`, `__str__`) that Python calls automatically.

### Examples from Your Codebase:

```python
# __init__ - Called when object is created
class LeaveManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# __str__ - Called when converting to string (if defined)
# Not used in your codebase, but here's how it would work:
class UserModel:
    def __str__(self):
        return f"UserModel class"

# __repr__ - Called for debugging (if defined)
# Not used in your codebase, but here's how it would work:
class UserModel:
    def __repr__(self):
        return f"UserModel()"
```

**Common Dunder Methods:**
- `__init__`: Constructor
- `__str__`: String representation
- `__repr__`: Developer representation
- `__len__`: Length of object
- `__eq__`: Equality comparison (`==`)

---

## 12. Decorators in OOP

### What are Decorators?
Decorators modify or enhance functions/methods. In OOP, they're used for static methods, class methods, and property methods.

### Examples from Your Codebase:

#### @staticmethod
```python
# models/user_model.py
class UserModel:
    @staticmethod
    async def user_registration(discord_id: int, name: str):
        # No 'self' needed
        pass
```

#### @app_commands.command
```python
# cogs/leave_management.py
class LeaveManagement(commands.Cog):
    @app_commands.command(
        name="leave_request",
        description="Request a leave from work"
    )
    async def leave_request(self, interaction: discord.Interaction):
        # Method is decorated to become a Discord command
        pass
```

#### @discord.ui.select
```python
# views/leave_management_views.py
class LeaveTypeSelectView(discord.ui.View):
    @discord.ui.select(
        placeholder="Select Leave Type",
        options=[...]
    )
    async def leave_type_select(self, interaction, select):
        # Method becomes a select dropdown in Discord
        pass
```

#### @discord.ui.button
```python
# views/leave_management_views.py
class ConfirmLeaveView(discord.ui.View):
    @discord.ui.button(label="Submit Request", style=discord.ButtonStyle.success)
    async def submit_request(self, interaction, button):
        # Method becomes a button in Discord
        pass
```

**Key Points:**
- Decorators modify method behavior
- `@staticmethod`: Makes method static
- `@app_commands.command`: Registers Discord command
- `@discord.ui.button`: Creates Discord button
- `@discord.ui.select`: Creates Discord dropdown

---

## 🎯 Summary: OOP Patterns in Your Codebase

### 1. **Model Classes** (Static Methods Pattern)
```python
class UserModel:
    @staticmethod
    async def get_user_by_discord_id(discord_id):
        # Utility methods, no instance needed
        pass
```

### 2. **Cog Classes** (Inheritance Pattern)
```python
class LeaveManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Instance attributes
    
    @app_commands.command(...)
    async def some_command(self, interaction):
        # Instance methods
        pass
```

### 3. **View Classes** (Inheritance + Composition)
```python
class LeaveTypeSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_leave_type = None  # Instance attribute
    
    @discord.ui.select(...)
    async def leave_type_select(self, interaction, select):
        # Uses composition: creates Modal objects
        modal = PaidLeaveModal()
```

### 4. **Modal Classes** (Inheritance Pattern)
```python
class PaidLeaveModal(discord.ui.Modal):
    # Class attributes
    start_date = discord.ui.TextInput(...)
    
    async def on_submit(self, interaction):
        # Instance method
        pass
```

### 5. **Custom Bot Class** (Inheritance + Method Overriding)
```python
class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(...)  # Call parent
    
    async def setup_hook(self):
        # Override parent method
        pass
    
    async def on_ready(self):
        # Override parent method
        pass
```

---

## 📝 Best Practices Used in Your Codebase

1. **Separation of Concerns**
   - Models: Database operations (static methods)
   - Cogs: Command handlers (instance methods)
   - Views: UI components (inheritance)

2. **Single Responsibility**
   - Each class has one clear purpose
   - UserModel: User operations
   - LeaveManagement: Leave commands
   - LeaveTypeSelectView: Leave type selection

3. **Code Reuse**
   - Inheritance from discord.py classes
   - Static methods in Models for shared functionality

4. **Encapsulation**
   - Instance attributes (`self.bot`) are private to the instance
   - Methods control access to data

---

## 🚀 Quick Reference

| Concept | Example | Location |
|---------|---------|----------|
| Class Definition | `class UserModel:` | models/user_model.py |
| Constructor | `def __init__(self, bot):` | cogs/leave_management.py |
| Instance Method | `async def leave_request(self, ...):` | cogs/leave_management.py |
| Static Method | `@staticmethod async def user_registration(...):` | models/user_model.py |
| Inheritance | `class CustomBot(commands.Bot):` | main.py |
| Method Override | `async def setup_hook(self):` | main.py |
| super() | `super().__init__(timeout=180)` | views/leave_management_views.py |
| Composition | `self.bot = bot` | cogs/leave_management.py |
| Decorator | `@app_commands.command(...)` | cogs/leave_management.py |

---

## 💡 Practice Exercises

1. **Create a new Model class** with static methods
2. **Create a new Cog class** that inherits from `commands.Cog`
3. **Create a new View class** that inherits from `discord.ui.View`
4. **Override a method** in your CustomBot class
5. **Use composition** to include a Model in a Cog

---

This guide covers all OOP concepts used in your codebase! Study the examples and try implementing similar patterns in your own code.






