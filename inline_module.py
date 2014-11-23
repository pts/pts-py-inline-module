# by pts@fazekas.hu at Sun Nov 23 21:39:17 CET 2014

"""Python 2.x module to define modules and submodules inline."""

def module(func):
  """Function decorator to define and import (sub)modules inline.

  Example:

    @module
    def foo():
      answer = 42
      @module
      def bar():
        import foo  # Required, won't see outer foo otherwise.
        assert foo.answer == 42
        raise DefineModule  # @module creates this symbol temporarily.
      raise DefineModule

  Use @module('extend') instead of @module to extend the functionality of a
  module already defined (i.e. member of sys.modules).

  When defining several modules which import others, define the others first,
  and then the `import' will work: it will fetch the module defined above.

  If there are two modules which import each other (directly or transitively),
  then it's impossible to define them with @module.

  As soon as the module is (being) defined with @module, Python won't
  attempt to find its soubmodules on disk, so all submodules should also be
  defined using @module.
  """
  import sys
  class DefineModule(Exception): pass
  def moddef_generic(func, module_name, do_update_globals_first,
                     is_extend_ok):
    module_obj = sys.modules.get(module_name)
    if not is_extend_ok and module_obj is not None:
      raise ValueError('Module already defined: ' + module_name)
    if do_update_globals_first:
      # Copy from locals to globals in the parent module, so the
      # currently-being-defined module will see symbols already defined in
      # the parent module.
      fr = sys._getframe(2)
      up_func_locals = fr.f_locals
      up_func_globals = fr.f_globals
      fr = None  # Save memory.
      for k, v in up_func_locals.iteritems():
        up_func_globals[k] = v
      up_func_locals = up_func_globals = None
    i = module_name.rfind('.')
    if i >= 0:
      parent_module_name = module_name[:i]
      if parent_module_name not in sys.modules:
        raise ValueError('Parent module not defined yet: ' + parent_module_name)
    else:
      parent_module_name = ''
    outer_module_prefix = module_name + '.'
    if module_obj is None:
      module_obj = type(__builtins__)(module_name)
    func_globals = module_obj.__dict__  # __name__ and __doc__ are already set.
    def submodule(func, outer_module_prefix=outer_module_prefix,
                  func_type=type(moddef_generic)):
      if func == 'extend':
        def submodule_low(func):
          if not isinstance(func, func_type):
            raise TypeError
          return moddef_generic(func, outer_module_prefix + func.func_name,
                                True, True)
        return submodule_low
      if not isinstance(func, func_type):
        raise TypeError
      return moddef_generic(func, outer_module_prefix + func.func_name,
                            True, False)
    func_globals['module'] = submodule
    func_globals['DefineModule'] = DefineModule
    func_globals['__builtins__']  = __builtins__
    func_globals['__file__'] = func.func_code.co_filename
    if func.__doc__ is not None:
      func_globals.setdefault('__doc__', func.__doc__)
    sys.modules[module_name] = module_obj
    try:
      exec func.func_code in func_globals
      func_locals = ()
    except DefineModule, e:
      func_locals = sys.exc_info()[2].tb_next.tb_frame.f_locals
    if func_locals is ():
      raise RuntimeError('Missing at the end of module-function %s: '
                         'raise DefineModule' % module_name)
    if func_globals.get('module') is submodule:
      del func_globals['module']
    del func_globals['DefineModule']
    for k, v in func_locals.iteritems():
      func_globals[k] = v
    if parent_module_name:
      sub_module_name = module_name[len(parent_module_name) + 1:]
      # Real `import' also does it that late.
      sys.modules[parent_module_name].__dict__[sub_module_name] = module_obj
    return module_obj  # We can't undefine this.
  if func == 'extend':
    def module_low(func):
      if not isinstance(func, type(moddef_generic)):
        raise TypeError
      return moddef_generic(func, func.func_name, False, True)
    return module_low
  if not isinstance(func, type(moddef_generic)):
    raise TypeError
  return moddef_generic(func, func.func_name, False, False)
