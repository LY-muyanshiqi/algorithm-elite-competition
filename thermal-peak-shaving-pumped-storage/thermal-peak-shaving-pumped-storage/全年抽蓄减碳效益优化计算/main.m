clear; clc;
NH=load('hydro.txt');  %
NW=load('wind.txt');   %
NP=load('solar.txt');  %
FH=load('FH.txt');    %
N=length(NH(:,1));
Zpump=1400; %
h=4;        %
Cprice=0.05; %(/CO2)

core_number= 8;   %
parpool('local',core_number);
% for i=1:10
parfor i=1:N
    Nh=NH(i,:);
    Nw=NW(i,:);
    Np=NP(i,:);
    L=FH(i,:);
    A(:,:,i)=nslde(Nh,Nw,Np,L,Zpump,h,Cprice);
end
save A.mat

for i=1:N
    best_num(i)=compromise_solution(A(:,:,i));
    AA(i,:)=A(best_num(i),:,i);
    solution(i,:)=A(best_num(i),1:23,i);
    Z_gain(i,1)=AA(i,24);
    Z_gain(i,2)=AA(i,25);
end
save AA.mat

for i=1:N
    [F1(i,:),F2(i,:),Npump(i,:),Nt(i,:),Nt2(i,:),L(i,:)]=process(AA(i,1:23),i);  %F1:  F2:
    a(i)=F2(i,3)-F1(i,3);
end
ce=F2(:,3)-F1(:,3); %kg
CE=sum(ce)/10000000; %t

pump=reshape(Npump',8760,1); %
NT_pump=reshape(Nt',8760,1); %
NT=reshape(Nt2',8760,1);     %
L=reshape(L',8760,1);        %
AAA=[pump,NT_pump,NT,L];

% i=6;
% Nh=NH(i,:);
% Nw=NW(i,:);
% Np=NP(i,:);
% L=FH(i,:);
% A(:,:,i)=nslde(Nh,Nw,Np,L,Zpump,h);



    