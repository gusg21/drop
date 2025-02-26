# Drop

Drop is a simple Python-based reflection code generator for C. It's meant to be as minimally intrusive into the language or development experience while still providing runtime type information! It's currently being battle tested on a proprietary game engine developed by [A Frog's Pond LLC](https://afrogspond.com/).

Drop is composed of two pieces: the Python-based code generator (`drop/`), and the C support library (`drop_lib/`). The support library contains definitions for the types that Drop generates code for, although theoretically you could use your own metadata types as well (see generation information below.)

## Installing

To integrate Drop into a C project, a few steps are needed:

1. **Add the C support library `drop_lib/` to your codebase**. A super basic CMakeLists.txt is provided, but all you really need to do is make the header accessible (`drop.h`) and make sure `drop.c` is included in your build.

2. **Create a `drop_config.json` file**. You probably want to put this in the root of your project for simplicity, but it doesn't really matter. See the `drop_config.json` section below for more info.

## Making a `drop_config.json`

A drop config looks something like this:

```jsonc
{
    // A list of directories to scan all the files in as input.
    "directories": [
        {
            // The path to the directory to scan.
            "headers": "path/to/a/source/directory/",

            // Where to generate the metadata for this directory. Usually into a special 
            // folder so it's not in the way.
            "output": "path/to/a/source/directory/_gen/meta.c",

            // How an include for another scanned file should be added to your code. 
            // For instance, if we scanned a file called "a.h" that has a struct referenced 
            // by another struct in "b.h", how should we turn those file names into include 
            // directives?
            "include_template": "#include \"{}\""
        }
    ],

    // Only scan files that match one of these regexes.
    "header_filter": [
        "(.*)\\.h"
    ],

    // Other paths to search for included headers in.
    "includes": [
        "library1/include/",
        "library2/include/"
    ],

    // Any compile defines you want.
    "defines": [],

    // The directory, relative to this JSON file, to pull templates from.
    "templates_directory": "drop_templates",

    // The main template to use.
    "meta_template_file": "meta.c"
}
```

**Example templates are provided in `drop_templates/`**, and they're probably sufficient for most projects. They use the **Jinja2** format for customization and templating.

## Generating

Make sure you install the `requirements.txt` into your Python installation, preferably in a venv!

To generate code for your project, just run drop.py (in `drop/`) with the path to your drop_config.json. This will iterate through your specified files, compile all needed information about your structures, and then create C source files for compilation in your build.

**NOTE: Make sure to include the generated output C file (see `drop_config.json`) in your build! Otherwise your type data won't be defined.**

## Using

The generated structures take the form `[struct name]_meta`, so usage might look something like this:

### `example.h`
```c
#include "drop.h"

struct example {
    char letter;
    uint32_t integer;
};
DROP_REFLECT_STRUCT(example); // Defines a constant of type "struct drop_type_s" called "example_meta" that contains our metadata.
```

### `example.c`
```c
#include <stdio.h>

void print_out_fields() {
    // Get the type info.
    struct drop_type_s* type = &example_meta;
    printf("Type %s\n", type->name);

    // Iterate through the fields.
    for (uint32_t field_index = 0; field_index < DROP_MAX_FIELD_COUNT; field_index++) {
        struct drop_field_s* field = &type.fields[field_index];

        // Ensure this field is valid.
        if (field->valid) {
            printf("\tField %s\n", type->name);
        }
    }
}
```
```
Type example
    Field letter
    Field integer
```

A drop_field_s contains not only the name as shown above, but also a pointer to the data within its struct. In the example above, assuming a char is 1 byte, the `integer` field would have an offset of 0x1. Each field also contains a pointer to its type, and importantly **if a type is not defined, fields of that type will not be processed.** This allows you to select which parts of your code you want to reflect and which you don't.

## License

The code in this repository is licensed under the **MIT** license.

## Credits

Written by Angus Goucher ([@gusg21](https://github.com/gusg21))

### Libraries used

- [eliben/pycparser](https://github.com/eliben/pycparser/tree/main)
- [pallets/jinja](https://github.com/pallets/jinja)