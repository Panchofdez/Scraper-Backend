import re

string="asdasd\u2019sdasd the world's\u2020 fastest"

print(string)
new_string = re.sub(r"[^\x00-\x7F]+", "", string)
print(new_string)