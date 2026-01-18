|file|purpose|
|-|-|
|dup_search.py |uses set theory to remove songs whose charts are already located in another folder|
|dup_search_v2.py| merges duplicate songs into one super folder based on priority list| 
|dup_search_v3.py| aggresively deletes duplicate songs based on priority list (abandoned)| 

Notes about v2 merging algorithm:  
If a directory in the src shares a name with a file (non dir) in the dest, the file will be trashed.  
Conflicting audio files will be naively tested for corruption, keeping non-corrupt files when possible.  

TODO (v2):  
- check same named wav and ogg files for corruption, delete corrupt one, otherwise keep ogg or wav based on arg/defaults
- progress monitor

