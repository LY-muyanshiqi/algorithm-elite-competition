function m=compromise_solution(s)
a(:,1)=s(:,24);
b(:,1)=s(:,25);
c(:,1)=s(:,26); % 第三个目标函数
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
a_max=[];a_min=[];b_max=[];b_min=[];c_max=[];c_min=[];
a_max=max(max(a)); a_min=min(min(a)); 
b_max=max(max(b)); b_min=min(min(b)); 
c_max=max(max(c)); c_min=min(min(c)); 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
for i=1:length(a(:,1))
    x(i,1)=(a_max-a(i,1))/(a_max-a_min);
    x(i,2)=(b_max-b(i,1))/(b_max-b_min); 
    x(i,3)=(c_max-c(i,1))/(c_max-c_min); % 第三个目标函数的归一化
end
X=sum(x');
[maxX,m]=max(X); 
best=s(m,1:23);
% [maxY,n]=max(Y); 
% X=X';Y=Y';
% Z(:,1)=sort(X);
% Z(:,2)=sort(Y);
% aaaaa=std(Nwp);
% figure 
% plot(Z)



