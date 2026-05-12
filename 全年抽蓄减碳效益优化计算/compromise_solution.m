function m=compromise_solution(s)
a(:,1)=s(:,24);
b(:,1)=s(:,25);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
a_max=[];a_min=[];b_max=[];b_min=[];
a_max=max(max(a)); a_min=min(min(a)); 
b_max=max(max(b)); b_min=min(min(b)); 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
for i=1:length(a(:,1))
    x(i,1)=(a_max-a(i,1))/(a_max-a_min);
    x(i,2)=(b_max-b(i,1))/(b_max-b_min); 
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



