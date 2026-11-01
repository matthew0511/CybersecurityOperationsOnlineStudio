/* Pure CSV parsing and inventory preview validation; no DOM or external requests. */
(function(root){
 'use strict';
 function parseCSV(text){
  if(typeof text!=='string'||text.length>2*1024*1024)throw Error('Choose a CSV file up to 2 MiB.');
  text=text.replace(/^\uFEFF/,'');const rows=[];let row=[],value='',quoted=false,closed=false,fieldStart=true;
  const field=()=>{row.push(value);value='';closed=false;fieldStart=true;};
  const line=()=>{field();if(row.some(v=>v.trim()!==''))rows.push(row);row=[];if(rows.length>1001)throw Error('Import at most 1,000 accounts plus a header row.');};
  for(let i=0;i<text.length;i++){
   const c=text[i];if(quoted){if(c==='"'){if(text[i+1]==='"'){value+='"';i++;}else{quoted=false;closed=true;}}else value+=c;continue;}
   if(closed&&c!==','&&c!=='\r'&&c!=='\n')throw Error('Unexpected text after a quoted CSV field.');
   if(c==='"'){if(!fieldStart)throw Error('Quotes inside a field must be escaped and the field quoted.');quoted=true;fieldStart=false;}
   else if(c===',')field();else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;line();}else{value+=c;fieldStart=false;}
  }
  if(quoted)throw Error('A quoted CSV field is not closed.');if(value!==''||row.length||closed)line();
  if(rows.length<2)throw Error('Include a header row and at least one account.');
  const headers=rows.shift().map(v=>v.trim());if(headers.some(v=>!v)||new Set(headers.map(v=>v.toLowerCase())).size!==headers.length)throw Error('CSV column names must be nonempty and unique.');
  if(headers.length>50||headers.some(v=>v.length>200))throw Error('Use at most 50 columns with names up to 200 characters.');
  if(rows.some(r=>r.length!==headers.length))throw Error('Every row must contain the same number of columns as the header.');
  return {headers,rows};
 }
 function accounts(csv,mapping){
  for(const key of ['account','system'])if(!Number.isInteger(mapping[key])||mapping[key]<0||mapping[key]>=csv.headers.length)throw Error('Map an Account and System column.');
  const selected=Object.values(mapping).filter(i=>Number.isInteger(i)&&i>=0);if(new Set(selected).size!==selected.length)throw Error('Map each source column only once.');
  return csv.rows.map((row,index)=>{
   const result={};for(const key of ['account','system','privileged','last_seen']){
    const column=mapping[key];if(column===undefined||column===-1){if(key==='privileged')result.privileged=false;continue;}
    if(!Number.isInteger(column)||column<0||column>=csv.headers.length)throw Error('Choose a valid column mapping.');
    const value=row[column].trim();if(key==='privileged'){
     if(!/^(true|false|yes|no|1|0)$/i.test(value))throw Error('Row '+(index+2)+': privileged access must be true/false, yes/no or 1/0.');result[key]=/^(true|yes|1)$/i.test(value);
    }else if(key==='last_seen'){
     if(value){const date=new Date(value+'T00:00:00Z');if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==value)throw Error('Row '+(index+2)+': last use must be a valid YYYY-MM-DD date.');result[key]=value;}
    }else{if(!value||value.length>140)throw Error('Row '+(index+2)+': '+key+' needs 1–140 characters.');result[key]=value;}
   }return result;
  });
 }
 const api={parseCSV,accounts};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.StudioCSV=api;
})(typeof globalThis!=='undefined'?globalThis:this);
