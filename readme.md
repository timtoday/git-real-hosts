# github hosts 工具

原理就是去找个具体IP，hosts指向、避免dns劫持
自动检测最快的IP ，并写入本地hosts文件，提高访问速度

## 更新日志
update at 2025-01-03
```
1、ipaddress.com 页面有更新，修复支持
2、增加windows Admin权限检查支持
3、增加domains.txt # 注释支持
4、async 优化ping效率
```

## 使用方法

```
pip install -r requirements.txt

python app.py
```
