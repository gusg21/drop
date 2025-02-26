from pycparser import c_parser, c_generator, c_ast, parse_file
import jinja2
import argparse
import os
import json
import re
import time


class DropField():
    def __init__(self, name: str, _type: str, is_array: bool = False, array_count: int = 0):
        self.name = name
        self.type = _type
        self.is_array = is_array
        self.array_count = array_count


class DropStruct():
    def __init__(self, name: str, fields: list[DropField]):
        self.name = name
        self.fields = fields

    def add_field(self, field: DropField):
        for existing_field in self.fields:
            if existing_field.name == field.name:
                print("Trying to add duplicate field name '{}' to struct '{}'!".format(
                    field.name, self.name))
                return  # Don't duplicate names

        self.fields.append(field)


class Drop():
    def __init__(self, config: any, config_base_path: str):
        self.c_parser = c_parser.CParser()

        self.config = config
        self.config_base_path = config_base_path

        self.generator = c_generator.CGenerator()

        self.ast_cache = {}
        self.all_structs: dict[str, any] = {}
        self.meta_data_struct_names: set[str] = set()

        self.meta = []
        self.include_base_names: set[str] = set()
        self.typedefs: dict[str, str] = {}

    def generate_c_code(self, my_ast):
        return self.generator.visit(my_ast)

    def matches_header_filter(self, file_name: str, header_filter: list[str] | None) -> bool:
        if header_filter == None:
            return True

        for filt in header_filter:
            if re.match(filt, file_name):
                return True

        return False

    def get_include_flags(self) -> list[str]:
        flags = []
        flags.append(
            "-I" + os.path.realpath(os.path.join(self.config_base_path, "tools/drop/fake_libc_include")))
        for include_path in self.config["includes"]:
            real_path = os.path.realpath(os.path.join(
                self.config_base_path, include_path))
            flags.append("-I" + real_path)

        return flags

    def parse_file(self, file_path: str):
        basename = os.path.basename(file_path)
        print("Parsing {}...".format(basename))

        args = ["-E", "-U_MSC_VER", "-U_WIN32", "-DDROP"]
        if self.config["defines"]:
            args.extend(self.config["defines"])
        args.extend(self.get_include_flags())

        ast: c_ast.FileAST = parse_file(
            file_path, use_cpp=True, cpp_path="clang", cpp_args=args, parser=self.c_parser)
        self.ast_cache[file_path] = ast
        for node in ast.ext:
            if type(node) == c_ast.Typedef:
                typedef_name = node.name
                if type(node.type) == c_ast.TypeDecl:
                    if type(node.type.type) == c_ast.Struct:
                        self.typedefs[typedef_name] = node.type.type.name
                    
            if type(node) == c_ast.Decl:
                if type(node.type) == c_ast.Struct:
                    struct_name = node.type.name
                    
                    if node.type.decls:
                        if len(node.type.decls) > 0: # Ignore non-declaration references.
                            self.all_structs[struct_name] = node

                if type(node.type) == c_ast.TypeDecl:
                    if type(node.type.type) == c_ast.Struct:
                        if "drop_meta_type_s" == node.type.type.name:
                            struct_name: str = node.type.declname[:node.type.declname.find(
                                "_meta")]

                            if struct_name not in self.all_structs:
                                print("Failed to find struct {}!".format(
                                    struct_name))

                            self.meta_data_struct_names.add(struct_name)
                            print("Selected struct {}...".format(struct_name))

                            self.include_base_names.add(basename)

    def parse_directory(self, directory_path: str, header_filter: list[str] | None):
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if self.matches_header_filter(file, header_filter):
                    self.parse_file(os.path.join(root, file))

    def parse(self):
        for directory in self.config["directories"]:
            self.parse_directory(os.path.realpath(os.path.join(
                self.config_base_path, directory)), self.config["header_filter"])

    def resolve_type(self, type_name: str):
        original_name = type_name
        resolved_name = type_name
        while resolved_name in self.typedefs:
            resolved_name = self.typedefs[resolved_name]
        print("Resolved {} -> {}.".format(original_name, resolved_name))
        return resolved_name

    def generate_meta_data(self):
        for meta_struct_name in self.meta_data_struct_names:
            struct_name = meta_struct_name
            struct = self.all_structs[meta_struct_name]
            drop_struct = DropStruct(struct_name, [])

            print(struct_name)

            for decl in struct.type.decls:
                if type(decl.type) == c_ast.TypeDecl:
                    field_name = decl.type.declname
                    field_type_name = self.resolve_type(decl.type.type.names[0])
                    drop_field = DropField(field_name, field_type_name)
                    drop_struct.add_field(drop_field)

                    print("> {} {}".format(field_type_name, field_name))
                elif type(decl.type) == c_ast.ArrayDecl:
                    field_name = decl.type.type.declname
                    field_type_name = self.resolve_type(decl.type.type.type.names[0])
                    field_array_count = decl.type.dim.value
                    
                    drop_field = DropField(field_name, field_type_name, is_array=True, array_count=field_array_count)
                    drop_struct.add_field(drop_field)

                    print("> {} {}[{}]".format(field_type_name, field_name, field_array_count))


            self.meta.append(drop_struct)

    def write_c_meta_data(self, directory_info):
        includes = [directory_info["include_template"].format(basename) for basename in self.include_base_names]

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.realpath(os.path.join(
                self.config_base_path, self.config["templates_directory"]))),
        )
        template = env.get_template(self.config["meta_template_file"])
        rendered_c = template.render(
            structs=self.meta, timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), includes=includes)
        
        # Create _gen directory.
        meta_c_path = os.path.realpath(os.path.join(self.config_base_path, directory_info["output"]))
        gen_directory = os.path.dirname(meta_c_path)
        if not os.path.exists(gen_directory):
            os.makedirs(gen_directory)

        with open(meta_c_path, "w+") as meta_c_file:
            meta_c_file.write(rendered_c)

def main():
    drop_header = R"""
 ______   ______  _____   _____ 
 |     \ |_____/ |     | |_____]
 |_____/ |    \_ |_____| |       (c)2025 A Frog's Pond LLC.
 """

    print(drop_header)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("config_file", help="path to the drop config")
    args = arg_parser.parse_args()

    config = None
    with open(args.config_file, "r") as config_json_file:
        config = json.loads(config_json_file.read())
    config_base_path = os.path.dirname(args.config_file)

    for directory_info in config["directories"]:
        drop = Drop(config, config_base_path)
        real_directory = os.path.realpath(
            os.path.join(config_base_path, directory_info["headers"]))
        drop.parse_directory(real_directory, config["header_filter"])
        drop.generate_meta_data()
        drop.write_c_meta_data(directory_info)


if __name__ == "__main__":
    main()
