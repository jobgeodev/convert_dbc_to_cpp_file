#!/usr/bin/env python3

import os
from os.path import basename
import re
import cantools
from pprint import pprint

FULL_FILE_BODY_FMT='''
#pragma once

{include_file}

{struct_define}

{struct_parse}

{struct_unpack}

'''    

STRUCT_DEFINE_FMT='''
struct {struct_name} {{
    {member}
    
    {struct_name}(){{
        {fun_init}
    }}
    
    void print(){{
        std::cout << \"{struct_name}:\" << std::endl
        {fun_print};
    }}
    
}};
'''
 

STRUCT_PARSE_FMT='''
    int PARSE_{message_name_upper}(const CanFrameData& can, T_{message_name_upper}& data) {{
        if ({space_name_upper}_{message_name_upper}_FRAME_ID != can.can_id){{
            return 1;
        }}

        {space_name}_{message_name_lower}_t tmp;
        if (0 != {space_name}_{message_name_lower}_unpack(&tmp, can.data, can.can_dlc)){{
            return 2;
        }}

        {fun_parse}

        return 0;
    }}
'''


STRUCT_UNPACK_FMT='''
    void UNPACK_{space_name_upper}(const CanFrameData& can, bool to_print) {{
        int ret = 0;
        {fun_unpack}
    }}
'''

def _canonical(value):
    """Replace anything but 'a-z', 'A-Z' and '0-9' with '_'.
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', value)


def camel_to_snake_case(value):
    value = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', value)
    value = re.sub(r'(_+)', '_', value)
    value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value).lower()
    value = _canonical(value)

    return value

class build_dbc_cpp_wrap():
    def __init__(self, work_dir, out_dir, namespace_prefix):
        self.work_dir = work_dir
        self.out_dir = out_dir
        self.namespace_prefix = namespace_prefix
        self.dbc_pairs = []
        self.include_files = []
        self.struct_defines = []

    def walk_dbc_files(self):
        self.dbc_pairs = []
        for root, dirs, files in os.walk(self.work_dir, topdown=False):
            for name in files:
                if name.endswith(".dbc"):
                    dbc = os.path.join(root, name)
                    stem, suffix = os.path.splitext(name)
                    nm = "{}_{}".format(self.namespace_prefix, stem)
                    v = (nm, dbc)
                    self.dbc_pairs.append(v)

    def run_can_tools(self):
        for namespace,dbcpath in self.dbc_pairs:
            sh = "cantools generate_c_source --database-name {} {}".format(namespace, dbcpath)
            val = os.system(sh)

            ret = "Ret:[{}] Exec:[{}]".format(val, sh)
            print(ret)

    def get_include_files(self):
        lines = ["#include <iostream>"]
        for namespace,dbcpath in self.dbc_pairs:
            inc = "#include \"{}.h\"".format(namespace)
            lines.append(inc)
        lines.append("")
        lines.append('#include \"can_frame_data.hpp\"')
        return '\n'.join(lines)



    def get_struct_defines(self):
        lines = []
        for namespace, dbcpath in self.dbc_pairs:
            db = cantools.database.load_file(dbcpath)
            
            for message in  db.messages:
                message_name = message.name
                message_name = camel_to_snake_case(message.name)
            
                signal_names = []
                member_lines = []
                init_lines = []
                print_lines = []
                for signal in message.signals:
                    signal_name = camel_to_snake_case(signal.name)
                    member_line = 'double {};'.format(signal_name.upper())
                    init_line = '{} = 0;'.format(signal_name.upper())
                    print_line = '<< \"    {0}:\" << {0} << std::endl'.format(signal_name.upper())
                    member_lines.append(member_line)
                    init_lines.append(init_line)
                    print_lines.append(print_line)
                    signal_names.append(signal_name)



                struct_name_txt = 'T_{}'.format(message_name.upper())
                member_txt = '\n'.join(member_lines)
                fun_init_txt = '\n'.join(init_lines)
                fun_print_txt = '\n'.join(print_lines)

                line = STRUCT_DEFINE_FMT.format(struct_name=struct_name_txt,member=member_txt,fun_init=fun_init_txt,fun_print=fun_print_txt)      
                lines.append(line)

        return '\n'.join(lines)

    def get_struct_parses(self):
        lines = []
        for namespace, dbcpath in self.dbc_pairs:
            db = cantools.database.load_file(dbcpath)             
            
            for message in  db.messages:
                message_name = message.name
                message_name = camel_to_snake_case(message.name)                   
            
                parse_lines = []
                for signal in message.signals:
                    signal_name = camel_to_snake_case(signal.name)                     
                    
                    parse_line = 'data.{0} = {1}_{2}_{3}_decode(tmp.{3});'.format(signal_name.upper(), namespace, message_name.lower(), signal_name.lower())                     
                    parse_lines.append(parse_line)
                     
 
                fun_parse_txt = '\n'.join(parse_lines)
                  

                line = STRUCT_PARSE_FMT.format(                                            
                                            space_name=namespace, 
                                            space_name_upper=namespace.upper(),
                                            message_name_lower=message_name.lower(),
                                            message_name_upper=message_name.upper(), 
                                            fun_parse=fun_parse_txt)       
                lines.append(line)

        return '\n'.join(lines)


    def get_struct_unpacks(self):
        lines = []
        for namespace, dbcpath in self.dbc_pairs:
            db = cantools.database.load_file(dbcpath)             
            
            unpack_messages = []
            for message in  db.messages:
                message_name = message.name
                message_name = camel_to_snake_case(message.name)    

                unpack_message = '''
                T_{message_name_upper} _{message_name_lower};                
                ret = PARSE_{message_name_upper}(can, _{message_name_lower});
                if(0==ret){{
                    if (to_print) {{
                        _{message_name_lower}.print();
                    }}                    
                }} else if (1==ret) {{
                }} else if (2==ret) {{
                    std::cout << "struct  T_{message_name_upper} data parse error." << std::endl; 
                }} 
                '''.format(message_name_lower=message_name.lower(), message_name_upper=message_name.upper())
                unpack_messages.append(unpack_message)

            line = STRUCT_UNPACK_FMT.format(space_name_upper=namespace.upper(), fun_unpack='\n'.join(unpack_messages))
            lines.append(line)

        return '\n'.join(lines)
        

        
    def get_file_body(self):
        include_file_txt = self.get_include_files()
        struct_define_txt = self.get_struct_defines()
        struct_parse_txt = self.get_struct_parses() 
        struct_unpack_txt = self.get_struct_unpacks()

        all_txt = FULL_FILE_BODY_FMT.format(include_file=include_file_txt,struct_define=struct_define_txt,struct_parse=struct_parse_txt,struct_unpack=struct_unpack_txt)
        
        with open("parse_can_data_skoda.hpp", "w+") as f:
            f.write(all_txt ) 
            f.close()

    def run(self):
        self.walk_dbc_files()
        self.run_can_tools()
        self.get_include_files()
        self.get_file_body()


if __name__ == "__main__" :
    
    work_dir = r'/home/wanhy/Project/Github/workspace/python/cantools/dbcs'    
    wrap = build_dbc_cpp_wrap(work_dir, ".", "Skoda")   
    wrap.run()
