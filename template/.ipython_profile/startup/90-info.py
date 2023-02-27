import types

print(sys.version)

def _imports():
    print("import ", end="")
    for name, val in globals().items():
        if isinstance(val, types.ModuleType) and val.__name__ != "builtins":
            if val.__name__ == name:
                print(f"{val.__name__}", end =", ")
            else:
                print(f"{val.__name__} as {name}", end =", ")

    print("\b\b ")

_imports()
