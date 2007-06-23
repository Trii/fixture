
"""Loadable fixtures

.. contents:: :local:

After defining data with the DataSet class you need some way to load the data for your test.  Each DataSet you want to load needs some storage medium, say, a `Data Mapper`_ or `Active Record`_ object.  A Fixture is simply an environment that knows how to load data using the right objects.  It puts the pieces together, if you will.

.. _Data Mapper: http://www.martinfowler.com/eaaCatalog/dataMapper.html
.. _Active Record: http://www.martinfowler.com/eaaCatalog/activeRecord.html

Supported storage media
~~~~~~~~~~~~~~~~~~~~~~~

To create a specific data-loading environment, the following subclasses are available:

SQLAlchemyFixture
    loads data using `Table`_ objects or `mapped classes`_ via the `sqlalchemy`_ 
    module
SQLObjectFixture
    loads data using `SQLObject classes`_ via the `sqlobject`_ module

The idea is that your application already defines its own way of accessing its data; the LoadableFixture just "hooks in" to that interface.  Before considering the Fixture, here is an example data model defined using `sqlalchemy`_::

    >>> from sqlalchemy import *
    >>> engine = create_engine('sqlite:///:memory:')
    >>> meta = BoundMetaData(engine)
    >>> session = create_session(engine)
    >>> authors = Table('authors', meta,
    ...     Column('id', Integer, primary_key=True),
    ...     Column('first_name', String),
    ...     Column('last_name', String))
    ... 
    >>> class Author(object):
    ...     pass
    ... 
    >>> mapper(Author, authors) #doctest: +ELLIPSIS
    <sqlalchemy.orm.mapper.Mapper object at ...>
    >>> books = Table('books', meta, 
    ...     Column('id', Integer, primary_key=True),
    ...     Column('title', String),
    ...     Column('author_id', Integer, ForeignKey('authors.id')))
    ... 
    >>> class Book(object):
    ...     pass
    ... 
    >>> mapper(Book, books) #doctest: +ELLIPSIS
    <sqlalchemy.orm.mapper.Mapper object at ...>
    >>> meta.create_all()

.. _sqlalchemy: http://www.sqlalchemy.org/
.. _Table: http://www.sqlalchemy.org/docs/tutorial.myt#tutorial_schemasql_table_creating
.. _mapped classes: http://www.sqlalchemy.org/docs/datamapping.myt
.. _sqlobject: http://sqlobject.org/
.. _SQLObject classes: http://sqlobject.org/SQLObject.html#declaring-the-class

Defining a Fixture
~~~~~~~~~~~~~~~~~~

Define a fixture object like so::

    >>> from fixture import SQLAlchemyFixture
    >>> dbfixture = SQLAlchemyFixture(
    ...     env={'BookData': Book, 'AuthorData': Author},
    ...     session=session )
    ... 

For the available keyword arguments of respective LoadableFixture objects, see `SQLAlchemyFixture API`_ and `SQLObjectFixture API`_.

.. _SQLAlchemyFixture API: ../apidocs/fixture.loadable.sqlalchemy_loadable.SQLAlchemyFixture.html
.. _SQLObjectFixture API: ../apidocs/fixture.loadable.sqlobject_loadable.SQLObjectFixture.html

.. note::
    - Any keyword attribute of a LoadableFixture can be set later on as an 
      attribute of the instance.
    - LoadableFixture instances can safely be module-level objects
    - An ``env`` can be a dict or a module
    
Loading DataSet objects
~~~~~~~~~~~~~~~~~~~~~~~

As mentioned earlier, a DataSet shouldn't have to know how to store itself; the job of the Fixture object is to load and unload DataSet objects.  Let's consider the following DataSet objects (reusing the examples from earlier)::

    >>> from fixture import DataSet
    >>> class AuthorData(DataSet):
    ...     class frank_herbert:
    ...         first_name="Frank"
    ...         last_name="Herbert"
    >>> class BookData(DataSet):
    ...     class dune:
    ...         title = "Dune"
    ...         author_id = AuthorData.frank_herbert.ref('id')

As you recall, we passed a dictionary into the Fixture that associates DataSet names with storage objects.  Using this dict, a Fixture.Data instance now knows to use the sqlalchemy mapped class ``Book`` when saving a DataSet named ``BookData``.  Since we also gave it a ``session`` keyword, this will be used to save objects::
    
    >>> data = dbfixture.data(AuthorData, BookData)
    >>> data.setup() 
    >>> list(session.query(Book).select()) #doctest: +ELLIPSIS
    [<...Book object at ...>]
    >>> data.teardown()
    >>> list(session.query(Book).select())
    []

Discovering storable objects with Style
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you didn't want to create a strict mapping of DataSet class names to their storable object names you can use Style objects to translate DataSet class names.  For example, consider this Fixture :

    >>> from fixture import SQLAlchemyFixture
    >>> from fixture.style import TrimmedNameStyle
    >>> dbfixture = SQLAlchemyFixture(
    ...     env=globals(),
    ...     style=TrimmedNameStyle(suffix="Data"),
    ...     session=session )
    ... 

This would take the name ``AuthorData`` and trim off "Data" from its name to find ``Author``, its mapped sqlalchemy class for storing data.  Since this is a logical convention to follow for naming DataSet classes, you can use a shortcut:

    >>> from fixture.style import NamedDataStyle
    >>> dbfixture = SQLAlchemyFixture(
    ...     env=globals(),
    ...     style=NamedDataStyle(),
    ...     session=session )
    ... 

See the `Style API`_ for all available Style objects.

.. _Style API: ../apidocs/fixture.style.html

Loading DataSet classes in a test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you have a Fixture object to load DataSet classes you are ready to write some tests.  You can either write your own code that creates a data instance and calls setup/teardown manually (like in previous examples), or you can use one of several utilities.  

As a hoky attempt to make these tests somewhat realistic, here is a function we will be testing, that returns True if a book by author or title is in stock:

    >>> def in_stock(book_title=None, author_last_name=None):
    ...     if book_title:
    ...         rs = session.query(Book).select(books.c.title==book_title)
    ...     elif author_last_name:
    ...         rs = session.query(Book).select(
    ...                 authors.c.last_name==author_last_name,
    ...                 from_obj=[books.join(authors)])
    ...     else:
    ...         return False
    ...     if len(list(rs)):
    ...         return True

Loading objects using DataTestCase
++++++++++++++++++++++++++++++++++

DataTestCase is a mixin class to use with Python's built-in ``unittest.TestCase``::

    >>> import unittest
    >>> from fixture import DataTestCase
    >>> class TestBookShop(DataTestCase, unittest.TestCase):
    ...     fixture = dbfixture
    ...     datasets = [BookData]
    ...
    ...     def test_books_are_in_stock(self):
    ...         assert in_stock(book_title=self.data.BookData.dune.title)
    ... 
    >>> suite = unittest.TestLoader().loadTestsFromTestCase(TestBookShop)
    >>> unittest.TextTestRunner().run(suite)
    <unittest._TextTestResult run=1 errors=0 failures=0>

Re-using what was created earlier, the ``fixture`` attribute is set to the Fixture instance and the ``datasets`` attribute is set to a list of DataSet classes.  When in the test method itself, as you can see, you can reference loaded data through ``self.data``, an instance of SuperSet.  Keep in mind that if you need to override either setUp() or tearDown() then you'll have to call the super methods.

See the `DataTestCase API`_ for a full explanation of how it can be configured.

.. _DataTestCase API: ../apidocs/fixture.util.DataTestCase.html
    

Loading objects using @dbfixture.with_data
++++++++++++++++++++++++++++++++++++++++++

If you use nose_, a test runner for Python, then you may be familiar with its `discovery of test methods`_.  Test methods (as opposed to unittest.TestCase classes) provide a quick way to write procedural tests and often illustrate concisely what features are being tested.  Nose supports test methods that are decorated with setup and teardown methods and fixture provides a way to setup/teardown DataSet objects for a test method.  If you don't have nose_ installed, simply install fixture like so and nose will be installed for you::
    
    easy_install fixture[decorators]

The special decorator method is an instance method of a Fixture class, ``with_data``; it can be used like so::

    >>> @dbfixture.with_data(AuthorData, BookData)
    ... def test_books_are_in_stock(data):
    ...     assert in_stock(book_title=data.BookData.dune.title)
    ... 
    >>> import nose
    >>> case = nose.case.FunctionTestCase(test_books_are_in_stock)
    >>> unittest.TextTestRunner().run(case)
    <unittest._TextTestResult run=1 errors=0 failures=0>

Like in the previous example, the ``data`` attribute is a SuperSet object you can use to reference loaded data.  This is passed to your decorated test method as its first argument.  Note that nose_ will run the above code automatically; the inline execution of the test here is merely for example.

See the `Fixture.Data.with_data API`_ for more information.

.. _nose: http://somethingaboutorange.com/mrl/projects/nose/
.. _discovery of test methods: http://code.google.com/p/python-nose/wiki/WritingTests
.. _Fixture.Data.with_data API: ../apidocs/fixture.base.Fixture.html#with_data

Loading objects using the with statement
++++++++++++++++++++++++++++++++++++++++

In Python 2.5 or later you can write test code in a more logical manner by using the `with statement`_.  Anywhere in your code, when you enter a with block using a Fixture.Data instance, the data is loaded and you have an instance in which to reference the data.  When you exit, the data is torn down for you, regardless of whether there was an exception or not.  For example::

    from __future__ import with_statement
    with dbfixture.data(AuthorData, BookData) as data:
        assert in_stock(book_title=data.BookData.dune.title)    

.. _with statement: http://www.python.org/dev/peps/pep-0343/

Defining a custom LoadableFixture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to create your own Fixture by just subclassing a few fixture classes.  If you create one that may be useful to others and would like to submit a patch, it would be gladly accepted.

You'll need to subclass at least `fixture.loadable.loadable:LoadableFixture`_, possibly even `fixture.loadable.loadable:EnvLoadableFixture`_ or the more useful `fixture.loadable.loadable:DBLoadableFixture`_.  Here is a simple example for creating a fixture that hooks into some kind of database-centric loading mechanism::

    >>> loaded_items = set()
    >>> class Author(object):
    ...     '''This would be your actual storage object, i.e. data mapper.
    ...        For the sake of brevity, you'll have to imagine that it knows 
    ...        how to somehow store "author" data.'''
    ... 
    ...     name = None # gets set by the data set
    ... 
    ...     def save(self):
    ...         '''just one example of how to save your object.
    ...            there is no signature guideline for how this object 
    ...            should save itself (see the adapter below).'''
    ...         loaded_items.add(self)
    ...     def __repr__(self):
    ...         return "<%s name=%s>" % (self.__class__.__name__, self.name)
    ...
    >>> from fixture.loadable import DBLoadableFixture
    >>> class MyFixture(DBLoadableFixture):
    ...     '''This is the class you will instantiate, the one that knows how to 
    ...        load datasets'''
    ... 
    ...     class Medium(DBLoadableFixture.Medium):
    ...         '''This is an object that adapts a Fixture storage medium 
    ...            to the actual storage medium.'''
    ... 
    ...         def clear(self, obj):
    ...             '''where you need to expunge the obj'''
    ...             loaded_items.remove(obj)
    ... 
    ...         def visit_loader(self, loader):
    ...             '''a chance to reference any attributes from the loader.
    ...                this is called before save().'''
    ... 
    ...         def save(self, row):
    ...             '''save data into your object using the provided 
    ...                fixture.dataset.DataRow instance'''
    ...             # instantiate your real object class (Author), which was set 
    ...             # in __init__ to self.medium ...
    ...             obj = self.medium() 
    ...             for c in row.columns():
    ...                 # column values become object attributes...
    ...                 setattr(obj, c, getattr(row, c))
    ...             obj.save()
    ...             # be sure to return the object:
    ...             return obj
    ... 
    ...     def create_transaction(self):
    ...         '''a chance to create a transaction.
    ...            two separate transactions are used: one during loading
    ...            and another during unloading.'''
    ...         class DummyTransaction(object):
    ...             def begin(self):
    ...                 pass
    ...             def commit(self): 
    ...                 pass
    ...             def rollback(self): 
    ...                 pass
    ...         t = DummyTransaction()
    ...         t.begin() # you must call begin yourself, if necessary
    ...         return t

Now let's load some data into the custom Fixture using a simple ``env`` mapping::

    >>> from fixture import DataSet
    >>> class AuthorData(DataSet):
    ...     class frank_herbert:
    ...         name="Frank Herbert"
    ...
    >>> fixture = MyFixture(env={'AuthorData': Author})
    >>> data = fixture.data(AuthorData)
    >>> data.setup()
    >>> loaded_items
    set([<Author name=Frank Herbert>])
    >>> data.teardown()
    >>> loaded_items
    set([])
    

.. _fixture.loadable.loadable:LoadableFixture: ../apidocs/fixture.loadable.loadable.LoadableFixture.html
.. _fixture.loadable.loadable:EnvLoadableFixture: ../apidocs/fixture.loadable.loadable.EnvLoadableFixture.html
.. _fixture.loadable.loadable:DBLoadableFixture: ../apidocs/fixture.loadable.loadable.DBLoadableFixture.html

.. api_only::
   The fixture.loadable module
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
# from __future__ import with_statement
import sys
from fixture.base import Fixture
from fixture.util import ObjRegistry, _mklog
from fixture.style import OriginalStyle
from fixture.dataset import Ref, dataset_registry, DataRow
from fixture.exc import LoadError, UnloadError
import logging

log     = _mklog("fixture.loadable")
treelog = _mklog("fixture.loadable.tree")

class LoadableFixture(Fixture):
    """knows how to load data into something useful.
    
    This is an abstract class and cannot be used directly.  You can use a 
    LoadableFixture that already knows how to load into a specific medium, 
    such as SQLAlchemyFixture, or create your own to build your own to load 
    DataSet objects into custom storage media.

    Keyword Arguments
    -----------------
    - dataclass
    
      - class to instantiate with datasets (defaults to that of Fixture)

    - style

      - a Style object to translate names with (defaults to NamedDataStyle)
 
    - medium

      - optional LoadableFixture.StorageMediumAdapter to store DataSet 
        objects with
    
    """
    style = OriginalStyle()
    dataclass = Fixture.dataclass
    
    def __init__(self, style=None, medium=None, dataclass=None):
        Fixture.__init__(self, loader=self, dataclass=dataclass)
        if style:
            self.style = style
        if medium:
            self.Medium = medium
    
    class StorageMediumAdapter(object):
        """common interface for working with storable objects.
        """
        def __init__(self, medium, dataset):
            self.medium = medium
            self.dataset = dataset
            self.transaction = None
        
        def __getattr__(self, name):
            return getattr(self.obj, name)
        
        def __repr__(self):
            return "%s at %s for %s" % (
                    self.__class__.__name__, hex(id(self)), self.medium)
            
        def clear(self, obj):
            """clear the stored object.
            """
            raise NotImplementedError
        
        def clearall(self):
            """clear all stored objects.
            """
            log.info("CLEARING stored objects for %s", self.dataset)
            for obj in self.dataset.meta._stored_objects:
                try:
                    self.clear(obj)
                except Exception, e:
                    etype, val, tb = sys.exc_info()
                    raise UnloadError(etype, val, self.dataset, 
                                         stored_object=obj), None, tb
            
        def save(self, row):
            """given a DataRow, save it somehow."""
            raise NotImplementedError
            
        def visit_loader(self, loader):
            """a chance to visit the LoadableFixture object."""
            pass
            
    Medium = StorageMediumAdapter
            
    class StorageMediaNotFound(LookupError):
        """Looking up a storable object failed."""
        pass
    
    class LoadQueue(ObjRegistry):
        """Keeps track of what class instances were loaded.
        
        "level" is used like so:
            
        The lower the level, the lower that object is on the foreign key chain.  
        As the level increases, this means more foreign objects depend on the 
        local object.  Thus, objects need to be unloaded starting at the lowest 
        level and working up.  Also, since objects can appear multiple times in 
        foreign key chains, the queue only acknowledges the object at its 
        highest level, since this will ensure all dependencies get unloaded 
        before it.  
        
        """

        def __init__(self):
            ObjRegistry.__init__(self)
            self.tree = {}
            self.limit = {}
        
        def __repr__(self):
            return "<%s at %s>" % (
                    self.__class__.__name__, hex(id(self)))
        
        def _pushid(self, id, level):
            if id in self.limit:
                # only store the object at its highest level:
                if level > self.limit[id]:
                    self.tree[self.limit[id]].remove(id)
                    del self.limit[id]
                else:
                    return
            self.tree.setdefault(level, [])
            self.tree[level].append(id)
            self.limit[id] = level
        
        def clear(self):
            ObjRegistry.clear(self)
            # this is an attempt to free up refs to database connections:
            self.tree = {}
            self.limit = {}
        
        def register(self, obj, level):
            """register this object as "loaded" at level
            """
            id = ObjRegistry.register(self, obj)
            self._pushid(id, level)
            return id
        
        def referenced(self, obj, level):
            """tell the queue that this object was referenced again at level.
            """
            id = self.id(obj)
            self._pushid(id, level)
        
        def to_unload(self):
            """yields a list of objects suitable for unloading.
            """
            level_nums = self.tree.keys()
            level_nums.sort()
            treelog.info("*** unload order ***")
            for level in level_nums:
                unload_queue = self.tree[level]
                verbose_obj = []
                
                for id in unload_queue:
                    obj = self.registry[id]
                    verbose_obj.append(obj.__class__.__name__)
                    yield obj
                
                treelog.info("%s. %s", level, verbose_obj)
    
    def attach_storage_medium(self):
        pass
    
    def begin(self, unloading=False):
        if not unloading:
            self.loaded = self.LoadQueue()
    
    def commit(self):
        raise NotImplementedError
    
    def load(self, data):
        def loader():
            for ds in data:
                self.load_dataset(ds)
        self.wrap_in_transaction(loader, unloading=False)
        
    def load_dataset(self, ds, level=1):
        """load this dataset and all its dependent datasets.
        
        level is essentially the order of processing (going from dataset to 
        dependent datasets).  Child datasets are always loaded before the 
        parent.  The level is important for visualizing the chain of 
        dependencies : 0 is the bottom, and thus should be the first set of 
        objects unloaded
        
        """
        is_parent = level==1
        
        levsep = is_parent and "/--------" or "|__.."
        treelog.info(
            "%s%s%s (%s)", level * '  ', levsep, ds.__class__.__name__, 
                                            (is_parent and "parent" or level))
        
        for ref_ds in ds.meta.references:
            r = ref_ds.shared_instance(default_refclass=self.dataclass)
            new_level = level+1
            self.load_dataset(r,  level=new_level)
        
        self.attach_storage_medium(ds)
        
        if ds in self.loaded:
            # keep track of its order but don't actually load it...
            self.loaded.referenced(ds, level)
            return
        
        log.info("LOADING rows in %s", ds)
        ds.meta.storage_medium.visit_loader(self)
        for key, row in ds:
            try:
                # resolve this row's referenced values :
                for k in row.columns():
                    v = getattr(row, k)
                    if isinstance(v, Ref.Value):
                        ref = v.ref
                        ref.dataset_obj = self.loaded[ref.dataset_class]
                        isref=True
                
                if not isinstance(row, DataRow):
                    row = row(ds)
                obj = ds.meta.storage_medium.save(row)
                ds.meta._stored_objects.store(key, obj)
                # save the instance in place of the class...
                ds._setdata(key, row)
                
            except Exception, e:
                etype, val, tb = sys.exc_info()
                raise LoadError(etype, val, ds, key=key, row=row), None, tb
        
        self.loaded.register(ds, level)
    
    def rollback(self):
        raise NotImplementedError
    
    def then_finally(self, unloading=False):
        pass
    
    def unload(self):
        def unloader():
            for dataset in self.loaded.to_unload():
                self.unload_dataset(dataset)
            self.loaded.clear()
            dataset_registry.clear()
        self.wrap_in_transaction(unloader, unloading=True)
    
    def unload_dataset(self, dataset):
        dataset.meta.storage_medium.clearall()
    
    def wrap_in_transaction(self, routine, unloading=False):
        self.begin(unloading=unloading)
        try:
            try:
                routine()
            except:
                self.rollback()
                raise
            else:
                self.commit()
        finally:
            self.then_finally(unloading=unloading)

class EnvLoadableFixture(LoadableFixture):
    """An abstract fixture that can resolve DataSet objects from an env.
    
    Keyword "env" should be a dict or a module if not None.
    According to the style rules, the env will be used to find objects by name.
    
    """
    def __init__(self, env=None, **kw):
        LoadableFixture.__init__(self, **kw)
        self.env = env
    
    def attach_storage_medium(self, ds):
        if ds.meta.storage_medium is not None:
            # already attached...
            return
        
        storable = ds.meta.storable
        
        if not storable:
            if not ds.meta.storable_name:
                ds.meta.storable_name = self.style.guess_storable_name(
                                                        ds.__class__.__name__)
        
            if hasattr(self.env, 'get'):
                storable = self.env.get(ds.meta.storable_name, None)
            if not storable:
                if hasattr(self.env, ds.meta.storable_name):
                    try:
                        storable = getattr(self.env, ds.meta.storable_name)
                    except AttributeError:
                        pass
        
            if not storable:
                repr_env = repr(type(self.env))
                if hasattr(self.env, '__module__'):
                    repr_env = "%s from '%s'" % (repr_env, self.env.__module__)
                
                raise self.StorageMediaNotFound(
                    "could not find %s '%s' for "
                    "dataset %s in self.env (%s)" % (
                        self.Medium, ds.meta.storable_name, ds, repr_env))
                        
        if storable == ds.__class__:
            raise ValueError(
                "cannot use %s %s as a storable object of itself! "
                "(perhaps your style object was not configured right?)" % (
                                        ds.__class__.__name__, ds.__class__))
        ds.meta.storage_medium = self.Medium(storable, ds)

class DBLoadableFixture(EnvLoadableFixture):
    """An abstract fixture that will be loadable into a database.
    
    More specifically, one that forces its implementation to run atomically 
    (within a begin/ commit/ rollback block).
    """
    def __init__(self, dsn=None, **kw):
        EnvLoadableFixture.__init__(self, **kw)
        self.dsn = dsn
        self.transaction = None
    
    def begin(self, unloading=False):
        EnvLoadableFixture.begin(self, unloading=unloading)
        self.transaction = self.create_transaction()
    
    def commit(self):
        self.transaction.commit()
    
    def create_transaction(self):
        raise NotImplementedError
    
    def rollback(self):
        self.transaction.rollback()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
