corner case, requires two passes:  
1 has ab  
2 has bc  
3 has cd  
  
2 will merge to 1  
3 will merge to 2  
  
1 has abc  
2 has cd  
3 has _  
  
update db...  
2nd pass...  
2 will merge to 1  
  
1 has abcd  
2 has _  
3 has _  

