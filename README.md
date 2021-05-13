# convert_dbc_to_cpp_file
this python file can convert dbc (canbus) to cpp(cplusplus) function 

## 步骤

### 1.  在python环境内安装 cantools
```
pip install cantools
```

### 2.  修改work_dir和namespace
```
    work_dir = r'/home/wanhy/Project/Github/workspace/python/cantools/dbcs'    
    wrap = build_dbc_cpp_wrap(work_dir, ".", "Skoda")   
    wrap.run()
```

### 3. 执行python文件
```
python  build_dbc_cpp_code.py
```

### 4. 格式化代码
```
vs code or qtcreater
```
