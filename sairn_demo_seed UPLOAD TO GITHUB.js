// SAIRN DEMO DATA SEED — Session 19
// Injects realistic demo data into all 10 apps via localStorage
// Run this in browser console on any SAIRN app page, OR inject before </body>
// Resets all apps to a rich, impressive demo state
// Michael L. Dibert — SAIRN Technologies

(function() {
  var today = new Date();
  var fmt = function(d) { return d.toISOString().split('T')[0]; };
  var daysAgo = function(n) { var d=new Date(today); d.setDate(d.getDate()-n); return fmt(d); };
  var daysAhead = function(n) { var d=new Date(today); d.setDate(d.getDate()+n); return fmt(d); };

  // ============================================================
  // SAIRNhr
  // ============================================================
  localStorage.setItem('sh_company_name', 'Pinnacle Industries LLC');
  localStorage.setItem('sh_employees', JSON.stringify([
    {id:'emp_001',firstName:'Sarah',lastName:'Mitchell',title:'VP of Operations',department:'Operations',email:'smitchell@pinnacle.com',phone:'216-555-0101',hireDate:daysAgo(720),empType:'Full-Time',pay:'115000',status:'Active',manager:'Michael Dibert',location:'Cleveland, OH'},
    {id:'emp_002',firstName:'James',lastName:'Torres',title:'Senior Sales Manager',department:'Sales',email:'jtorres@pinnacle.com',phone:'216-555-0102',hireDate:daysAgo(540),empType:'Full-Time',pay:'88000',status:'Active',manager:'Sarah Mitchell',location:'Cleveland, OH'},
    {id:'emp_003',firstName:'Aisha',lastName:'Washington',title:'HR Business Partner',department:'Human Resources',email:'awashington@pinnacle.com',phone:'216-555-0103',hireDate:daysAgo(365),empType:'Full-Time',pay:'72000',status:'Active',manager:'Sarah Mitchell',location:'Cleveland, OH'},
    {id:'emp_004',firstName:'Derek',lastName:'Cho',title:'Software Engineer',department:'Technology',email:'dcho@pinnacle.com',phone:'216-555-0104',hireDate:daysAgo(180),empType:'Full-Time',pay:'95000',status:'Active',manager:'Sarah Mitchell',location:'Remote'},
    {id:'emp_005',firstName:'Maria',lastName:'Gonzalez',title:'Account Executive',department:'Sales',email:'mgonzalez@pinnacle.com',phone:'216-555-0105',hireDate:daysAgo(90),empType:'Full-Time',pay:'65000',status:'Active',manager:'James Torres',location:'Cleveland, OH'}
  ]));
  localStorage.setItem('sh_payroll', JSON.stringify([
    {name:'Sarah Mitchell',gross:4423.08,type:'FT',deductions:0},
    {name:'James Torres',gross:3384.62,type:'FT',deductions:0},
    {name:'Aisha Washington',gross:2769.23,type:'FT',deductions:0},
    {name:'Derek Cho',gross:3653.85,type:'FT',deductions:0},
    {name:'Maria Gonzalez',gross:2500.00,type:'FT',deductions:0}
  ]));
  localStorage.setItem('sh_pto_balances', JSON.stringify([
    {name:'Sarah Mitchell',balance:18.5,used:6.5,accrued:25},
    {name:'James Torres',balance:12.0,used:8.0,accrued:20},
    {name:'Aisha Washington',balance:9.5,used:5.5,accrued:15},
    {name:'Derek Cho',balance:14.0,used:1.0,accrued:15},
    {name:'Maria Gonzalez',balance:7.5,used:0,accrued:7.5}
  ]));
  localStorage.setItem('sh_recognitions', JSON.stringify([
    {from:'Sarah Mitchell',to:'Derek Cho',badge:'Innovation Star',points:500,message:'Built our new client dashboard in record time — outstanding work.',date:daysAgo(3),isBonus:false},
    {from:'James Torres',to:'Maria Gonzalez',badge:'Top Performer',points:300,message:'Closed the Henderson account — $240K deal. Incredible.',date:daysAgo(7),isBonus:false},
    {from:'Michael Dibert',to:'Aisha Washington',badge:'Culture Champion',points:400,message:'Transformed our onboarding experience. New hires love it.',date:daysAgo(14),isBonus:false}
  ]));
  localStorage.setItem('sh_time', JSON.stringify([
    {empName:'Maria Gonzalez',date:daysAgo(1),clockIn:'8:02am',clockOut:'5:18pm',hours:9.3,project:'Client Outreach'},
    {empName:'Derek Cho',date:daysAgo(1),clockIn:'9:00am',clockOut:'6:45pm',hours:9.75,project:'Dashboard v2'},
    {empName:'James Torres',date:daysAgo(2),clockIn:'7:45am',clockOut:'4:30pm',hours:8.75,project:'Q3 Sales Campaign'}
  ]));
  localStorage.setItem('sairnhr_pulse', JSON.stringify({score:78,responses:4,date:daysAgo(7)}));

  // ============================================================
  // SAIRNacc
  // ============================================================
  localStorage.setItem('sa_contacts', JSON.stringify([
    {id:'c001',name:'Henderson Construction',type:'Customer',email:'billing@henderson.com',phone:'216-555-0200',balance:24800},
    {id:'c002',name:'Apex Materials Inc.',type:'Vendor',email:'ap@apexmat.com',phone:'216-555-0201',balance:-8400},
    {id:'c003',name:'Westlake Properties',type:'Customer',email:'karen@westlakeprop.com',phone:'216-555-0202',balance:12600},
    {id:'c004',name:'Gordon Supply Co.',type:'Vendor',email:'orders@gordonsupply.com',phone:'216-555-0203',balance:-3200}
  ]));
  localStorage.setItem('sa_invoices', JSON.stringify([
    {id:'INV-2026-041',customer:'Henderson Construction',date:daysAgo(5),due:daysAhead(25),amount:24800,paid:0,status:'Outstanding',memo:'June services'},
    {id:'INV-2026-040',customer:'Westlake Properties',date:daysAgo(12),due:daysAhead(18),amount:12600,paid:0,status:'Outstanding',memo:'May-June retainer'},
    {id:'INV-2026-039',customer:'Meridian Group',date:daysAgo(35),due:daysAgo(5),amount:8200,paid:0,status:'Overdue',memo:'April services'},
    {id:'INV-2026-038',customer:'Blue Harbor LLC',date:daysAgo(42),due:daysAgo(12),amount:5400,paid:5400,status:'Paid',memo:'Q1 consulting'}
  ]));
  localStorage.setItem('sa_gl', JSON.stringify([
    {id:'GL001',date:daysAgo(3),account:'Revenue',description:'Henderson Construction — Invoice INV-2026-041',debit:0,credit:24800,ref:'INV-2026-041'},
    {id:'GL002',date:daysAgo(5),account:'Accounts Payable',description:'Apex Materials — Materials delivery',debit:8400,credit:0,ref:'AP-2026-188'},
    {id:'GL003',date:daysAgo(7),account:'Payroll Expense',description:'Bi-weekly payroll — 5 employees',debit:16730.78,credit:0,ref:'PAY-2026-12'},
    {id:'GL004',date:daysAgo(10),account:'Revenue',description:'Westlake Properties — retainer',debit:0,credit:12600,ref:'INV-2026-040'}
  ]));
  localStorage.setItem('sa_inventory', JSON.stringify([
    {sku:'MAT-001',name:'Calacatta Gold Slab',category:'Natural Stone',qty:8,cost:850,price:1400,reorder:3},
    {sku:'MAT-002',name:'Quartz White Carrara',category:'Engineered Stone',qty:14,cost:620,price:980,reorder:5},
    {sku:'MAT-003',name:'Absolute Black Granite',category:'Natural Stone',qty:6,cost:480,price:820,reorder:4},
    {sku:'SUP-001',name:'Diamond Blade 14"',category:'Supplies',qty:3,cost:180,price:280,reorder:5}
  ]));
  localStorage.setItem('sa_bills', JSON.stringify([
    {id:'BILL-088',vendor:'Apex Materials Inc.',date:daysAgo(5),due:daysAhead(25),amount:8400,status:'Unpaid',category:'Cost of Goods'},
    {id:'BILL-087',vendor:'Gordon Supply Co.',date:daysAgo(12),due:daysAhead(18),amount:3200,status:'Unpaid',category:'Supplies'},
    {id:'BILL-086',vendor:'Cleveland Electric',date:daysAgo(30),due:daysAgo(0),amount:1240,status:'Paid',category:'Utilities'}
  ]));

  // ============================================================
  // SAIRNbuild
  // ============================================================
  localStorage.setItem('sb_clients', JSON.stringify([
    {id:'cli001',name:'Tom Henderson',company:'Henderson Residence',email:'tom@henderson.com',phone:'216-555-0300',address:'142 Oak Drive, Westlake OH 44145',type:'Residential'},
    {id:'cli002',name:'Maria Garcia',company:'Garcia Kitchen Remodel',email:'mgarcia@email.com',phone:'216-555-0301',address:'88 Elm Street, Avon OH 44011',type:'Residential'},
    {id:'cli003',name:'Davis Commercial Group',company:'Davis Office Build-Out',email:'proj@daviscommercial.com',phone:'216-555-0302',address:'400 Commerce Pkwy, Rocky River OH 44116',type:'Commercial'}
  ]));
  localStorage.setItem('sb_projects', JSON.stringify([
    {id:'proj001',name:'Henderson Kitchen Renovation',client:'Tom Henderson',value:68400,start:daysAgo(45),end:daysAhead(30),status:'In Progress',pctComplete:62,super:'Mike R.',address:'142 Oak Drive, Westlake OH'},
    {id:'proj002',name:'Garcia Full Kitchen Remodel',client:'Maria Garcia',value:42800,start:daysAgo(10),end:daysAhead(55),status:'In Progress',pctComplete:18,super:'Dave K.',address:'88 Elm Street, Avon OH'},
    {id:'proj003',name:'Davis Office Build-Out',client:'Davis Commercial Group',value:124000,start:daysAhead(14),end:daysAhead(90),status:'Scheduled',pctComplete:0,super:'TBD',address:'400 Commerce Pkwy, Rocky River OH'}
  ]));
  localStorage.setItem('sb_subs', JSON.stringify([
    {id:'sub001',name:'Premier Electric',trade:'Electrical',contact:'Joe Walsh',phone:'216-555-0410',license:'EC-2241',insurance:'Current',rate:95,project:'proj001'},
    {id:'sub002',name:'Aqua Plumbing',trade:'Plumbing',contact:'Dan Torres',phone:'216-555-0411',license:'PL-8832',insurance:'Current',rate:85,project:'proj001'},
    {id:'sub003',name:'Artistic Tile Co.',trade:'Tile',contact:'Maria R.',phone:'216-555-0412',license:'GC-1122',insurance:'Current',rate:75,project:'proj002'}
  ]));
  localStorage.setItem('sb_budget', JSON.stringify([
    {project:'proj001',category:'Labor',budgeted:28000,committed:24800,actual:18200},
    {project:'proj001',category:'Materials',budgeted:22000,committed:21400,actual:19800},
    {project:'proj001',category:'Subcontractors',budgeted:14000,committed:14000,actual:8400},
    {project:'proj001',category:'Permits & Fees',budgeted:2400,committed:2400,actual:2400},
    {project:'proj001',category:'Contingency',budgeted:2000,committed:0,actual:0}
  ]));

  // ============================================================
  // SAIRNlaw
  // ============================================================
  localStorage.setItem('sl_firm_name', 'Dibert & Associates Law Group');
  localStorage.setItem('sl_clients', JSON.stringify([
    {id:'cli001',name:'Thomas Henderson',type:'Individual',email:'t.henderson@email.com',phone:'216-555-0500',address:'142 Oak Drive, Westlake OH',status:'Active',since:daysAgo(180)},
    {id:'cli002',name:'Apex Industries LLC',type:'Corporate',email:'legal@apexind.com',phone:'216-555-0501',address:'400 Commerce Pkwy, Rocky River OH',status:'Active',since:daysAgo(365)},
    {id:'cli003',name:'Maria Garcia',type:'Individual',email:'mgarcia@email.com',phone:'216-555-0502',address:'88 Elm St, Avon OH',status:'Active',since:daysAgo(90)}
  ]));
  localStorage.setItem('sl_matters', JSON.stringify([
    {id:'mat001',name:'Henderson v. Lakewood Contractors',client:'Thomas Henderson',type:'Civil Litigation',status:'Active',opened:daysAgo(120),rate:350,retainer:5000,billed:8400,collected:5000,nextAction:'Deposition prep — '+daysAhead(7)},
    {id:'mat002',name:'Apex Industries — Commercial Lease Review',client:'Apex Industries LLC',type:'Transactional',status:'Active',opened:daysAgo(30),rate:300,retainer:3000,billed:1800,collected:3000,nextAction:'Lease redline due — '+daysAhead(3)},
    {id:'mat003',name:'Garcia Estate Planning',client:'Maria Garcia',type:'Estate Planning',status:'Active',opened:daysAgo(45),rate:275,retainer:2500,billed:1100,collected:2500,nextAction:'Will signing — '+daysAhead(14)}
  ]));
  localStorage.setItem('sl_time', JSON.stringify([
    {matter:'Henderson v. Lakewood Contractors',date:daysAgo(1),hours:3.5,rate:350,amount:1225,description:'Research — contractor liability precedents',billed:false},
    {matter:'Apex Industries — Commercial Lease Review',date:daysAgo(2),hours:2.0,rate:300,amount:600,description:'Initial lease review and redline',billed:false},
    {matter:'Garcia Estate Planning',date:daysAgo(3),hours:1.5,rate:275,amount:412.50,description:'Client meeting — asset inventory',billed:true}
  ]));
  localStorage.setItem('sl_deadlines', JSON.stringify([
    {matter:'Henderson v. Lakewood Contractors',deadline:daysAhead(7),type:'Deposition',description:'Client deposition — prepare witness',priority:'High'},
    {matter:'Apex Industries — Commercial Lease Review',deadline:daysAhead(3),type:'Filing',description:'Return redlined lease to opposing counsel',priority:'Critical'},
    {matter:'Garcia Estate Planning',deadline:daysAhead(14),type:'Signing',description:'Will execution ceremony',priority:'Medium'}
  ]));

  // ============================================================
  // SAIRNcare
  // ============================================================
  localStorage.setItem('sc_residents', JSON.stringify([
    {id:'res001',name:'Eleanor Thompson',room:'101A',dob:'1938-04-12',age:88,admitDate:daysAgo(420),payer:'Medicare',status:'Active',physician:'Dr. Patel',diagnoses:['CHF','Type 2 Diabetes','Hypertension'],dnr:true,allergies:'Penicillin'},
    {id:'res002',name:'Harold Johnson',room:'102B',dob:'1942-08-22',age:83,admitDate:daysAgo(180),payer:'Medicaid',status:'Active',physician:'Dr. Williams',diagnoses:['COPD','Osteoarthritis'],dnr:false,allergies:'Sulfa'},
    {id:'res003',name:'Dorothy Chen',room:'105A',dob:'1935-11-05',age:90,admitDate:daysAgo(730),payer:'Private Pay',status:'Active',physician:'Dr. Patel',diagnoses:['Dementia','HTN','Osteoporosis'],dnr:true,allergies:'None'},
    {id:'res004',name:'Robert Martinez',room:'108C',dob:'1940-03-18',age:86,admitDate:daysAgo(60),payer:'Medicare',status:'Active',physician:'Dr. Lee',diagnoses:['Hip Fracture — Post-Op','Atrial Fibrillation'],dnr:false,allergies:'Aspirin'},
    {id:'res005',name:'Agnes Wilson',room:'110A',dob:'1932-07-30',age:93,admitDate:daysAgo(910),payer:'Medicaid',status:'Active',physician:'Dr. Patel',diagnoses:['Advanced Dementia','CHF','Dysphagia'],dnr:true,allergies:'Latex'}
  ]));
  localStorage.setItem('care_residents', localStorage.getItem('sc_residents'));

  // ============================================================
  // SAIRNvet
  // ============================================================
  localStorage.setItem('sairnvet_patients', JSON.stringify([
    {id:'pat001',name:'Max',species:'Canine',breed:'Labrador Retriever',dob:'2019-03-15',age:7,owner:'John Smith',ownerPhone:'216-555-0600',ownerEmail:'jsmith@email.com',weight:68,status:'Active',lastVisit:daysAgo(14),vaccines:{rabies:daysAhead(180),dhpp:daysAhead(90),bordetella:daysAgo(30)},microchip:'985112010484321'},
    {id:'pat002',name:'Luna',species:'Feline',breed:'Domestic Shorthair',dob:'2020-08-22',age:5,owner:'Sarah Lee',ownerPhone:'216-555-0601',ownerEmail:'slee@email.com',weight:9.2,status:'Active',lastVisit:daysAgo(7),vaccines:{rabies:daysAhead(270),fvrcp:daysAhead(200)},microchip:'985112010491882'},
    {id:'pat003',name:'Bella',species:'Canine',breed:'Golden Retriever',dob:'2021-05-10',age:5,owner:'Chris Davis',ownerPhone:'216-555-0602',ownerEmail:'cdavis@email.com',weight:58,status:'Hospitalized',lastVisit:daysAgo(2),vaccines:{rabies:daysAhead(120),dhpp:daysAhead(60)},microchip:'985112010498341'}
  ]));
  localStorage.setItem('sairn_vet_appts', JSON.stringify([
    {patient:'Max',owner:'John Smith',date:fmt(today),time:'09:00',type:'Sick Visit',dvm:'Dr. Williams',reason:'Lethargy, decreased appetite x3 days'},
    {patient:'Luna',owner:'Sarah Lee',date:fmt(today),time:'10:30',type:'Wellness',dvm:'Dr. Patel',reason:'Annual exam + vaccines'},
    {patient:'Rocky',owner:'Amy Chen',date:daysAhead(1),time:'14:00',type:'Recheck',dvm:'Dr. Williams',reason:'Post-op suture check'}
  ]));
  localStorage.setItem('sairnhr_payroll_enrolled', JSON.stringify([
    {id:'emp_001',name:'Sarah Mitchell',payType:'salary',rate:115000,status:'active',enrolledDate:daysAgo(1)},
    {id:'emp_002',name:'James Torres',payType:'salary',rate:88000,status:'active',enrolledDate:daysAgo(1)},
    {id:'emp_003',name:'Aisha Washington',payType:'salary',rate:72000,status:'active',enrolledDate:daysAgo(1)},
    {id:'emp_004',name:'Derek Cho',payType:'salary',rate:95000,status:'active',enrolledDate:daysAgo(1)},
    {id:'emp_005',name:'Maria Gonzalez',payType:'salary',rate:65000,status:'active',enrolledDate:daysAgo(1)}
  ]));

  // ============================================================
  // StoneDesk
  // ============================================================
  localStorage.setItem('fab_shop_name', 'Pinnacle Stone & Design');
  localStorage.setItem('fab_shop_addr', '1240 Commerce Pkwy, Westlake OH 44145');
  localStorage.setItem('fab_shop_phone', '216-555-0700');
  localStorage.setItem('fab_shop_email', 'quotes@pinnaclestone.com');
  localStorage.setItem('sd_customers', JSON.stringify([
    {id:'cust001',name:'Henderson, Tom',email:'tom@henderson.com',phone:'216-555-0300',address:'142 Oak Drive, Westlake OH',type:'Retail',totalJobs:3,totalValue:12840},
    {id:'cust002',name:'Garcia, Maria',email:'mgarcia@email.com',phone:'216-555-0301',address:'88 Elm Street, Avon OH',type:'Retail',totalJobs:1,totalValue:4200},
    {id:'cust003',name:'Westlake Kitchen & Bath',email:'orders@wkb.com',phone:'216-555-0303',address:'400 Center Ridge Rd, Westlake OH',type:'Contractor',totalJobs:24,totalValue:186400}
  ]));
  localStorage.setItem('sd_jobs', JSON.stringify([
    {id:'SD-2026-0847',customer:'Henderson, Tom',address:'142 Oak Drive, Westlake OH',material:'Calacatta Gold',edge:'Eased',sqft:42,price:4800,status:'In Fabrication',installDate:daysAhead(5),created:daysAgo(14),depositPaid:2400,balance:2400},
    {id:'SD-2026-0848',customer:'Garcia, Maria',address:'88 Elm Street, Avon OH',material:'White Carrara Quartz',edge:'Full Bullnose',sqft:28,price:2800,status:'Template Scheduled',installDate:daysAhead(12),created:daysAgo(3),depositPaid:1400,balance:1400},
    {id:'SD-2026-0846',customer:'Westlake Kitchen & Bath',address:'204 Pine Ave, Bay Village OH',material:'Absolute Black Granite',edge:'Bevel',sqft:68,price:5240,status:'Installed',installDate:daysAgo(2),created:daysAgo(21),depositPaid:5240,balance:0}
  ]));
  localStorage.setItem('sd_inventory', JSON.stringify([
    {id:'slab001',material:'Calacatta Gold',vendor:'Stone Source LLC',size:'120x62',thickness:'3cm',qty:6,cost:850,status:'In Stock',location:'Row A-3'},
    {id:'slab002',material:'White Carrara Quartz',vendor:'MSI Surfaces',size:'126x63',thickness:'3cm',qty:10,cost:620,status:'In Stock',location:'Row B-1'},
    {id:'slab003',material:'Absolute Black Granite',vendor:'Stone Source LLC',size:'118x60',thickness:'3cm',qty:4,cost:480,status:'In Stock',location:'Row C-2'},
    {id:'slab004',material:'Taj Mahal Quartzite',vendor:'Premium Stone',size:'124x62',thickness:'3cm',qty:2,cost:920,status:'Low Stock',location:'Row A-7'}
  ]));
  localStorage.setItem('quoteCounter', '847');

  // ============================================================
  // SAIRNcode
  // ============================================================
  localStorage.setItem('sc_stats', JSON.stringify({
    queriesRun: 847,
    codesValidated: 2341,
    auditsCompleted: 124,
    accuracyRate: 98.2,
    lastUpdated: fmt(today)
  }));

  // ============================================================
  // Privacy accepted — skip splash on all apps
  // ============================================================
  localStorage.setItem('sairn_privacy_accepted', 'true');
  localStorage.setItem('_s_', 'demo');

  console.log('%c SAIRN Demo Data Loaded Successfully ', 'background:#6366F1;color:#fff;font-size:14px;padding:6px 12px;border-radius:4px;font-weight:700;');
  console.log('Apps seeded: SAIRNhr, SAIRNacc, SAIRNbuild, SAIRNlaw, SAIRNcare, SAIRNvet, StoneDesk, SAIRNcode');

})();
