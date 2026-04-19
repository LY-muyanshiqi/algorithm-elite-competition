clear; clc;
NH=load('hydro.txt');  %水电
NW=load('wind.txt');   %风电
NP=load('solar.txt');  %光伏
FH=load('FH.txt');    %陕西负荷
N=length(NH(:,1));
Zpump=140; %抽蓄规模
h=4;        %抽蓄满发小时

core_number= 8;   %并行计算
parpool('local',core_number);
% for i=1:10
parfor i=1:N
    Nh=NH(i,:);
    Nw=NW(i,:);
    Np=NP(i,:);
    L=FH(i,:);
    A(:,:,i)=nslde(Nh,Nw,Np,L,Zpump,h);
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
    [F1(i,:),F2(i,:),Npump(i,:),Nt(i,:),Nt2(i,:),L(i,:)]=process(AA(i,1:23),i);  %F1:有抽蓄下的火电调峰容量、日碳排放强度、日碳排放量  F2:无抽蓄下的火电调峰容量、日碳排放强度、日碳排放量
    a(i)=F2(i,3)-F1(i,3);
end
ce=F2(:,3)-F1(:,3); %逐日的抽蓄碳减排效益，单位kg
CE=sum(ce)/10000000; %全年的抽蓄碳减排效益，单位万t

pump=reshape(Npump',8760,1); %抽水蓄能电站运行过程
NT_pump=reshape(Nt',8760,1); %有抽蓄下火电运行过程
NT=reshape(Nt2',8760,1);     %无抽蓄下火电运行过程
L=reshape(L',8760,1);        %负荷
AAA=[pump,NT_pump,NT,L];

% i=6;
% Nh=NH(i,:);
% Nw=NW(i,:);
% Np=NP(i,:);
% L=FH(i,:);
% A(:,:,i)=nslde(Nh,Nw,Np,L,Zpump,h);



    