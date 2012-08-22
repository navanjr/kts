/* --- Script © 2005 EC Software --- */
var ua = navigator.userAgent;
var dom = (document.getElementById) ? true : false;
var ie4 = (document.all && !dom) ? true : false;
var ie5_5 = ((ua.indexOf("MSIE 5.5")>=0 || ua.indexOf("MSIE 6")>=0) && ua.indexOf("Opera")<0) ? true : false;
var ns4 = (document.layers && !dom) ? true : false;
var offsxy = 6;
function hmshowPopup(e, txt, stick) {
  var tip = '<table  border="1" cellpadding="6" cellspacing="0" bgcolor="#FFFFFF" style="{border-width:1px; border-color:#000000; border-collapse:collapse;}"><tr valign=top><td>'+ txt + '<\/td><\/tr><\/table>';
  var tooltip = atooltip();
  e = e?e:window.event;
  var mx = ns4 ? e.PageX : e.clientX;
  var my = ns4 ? e.PageY : e.clientY;
  var bodyl = (window.pageXOffset) ? window.pageXOffset : document.body.scrollLeft;
  var bodyt = (window.pageYOffset) ? window.pageYOffset : document.body.scrollTop;
  var bodyw = (window.innerWidth)  ? window.innerWidth  : document.body.offsetWidth;
  if (ns4) {
    tooltip.document.write(tip);
    tooltip.document.close();
    if ((mx + offsxy + bodyl + tooltip.width) > bodyw) { mx = bodyw - offsxy - bodyl - tooltip.width; if (mx < 0) mx = 0; }
    tooltip.left = mx + offsxy + bodyl;
    tooltip.top = my + offsxy + bodyt;
  }
  else {
    tooltip.innerHTML = tip;
    if (tooltip.offsetWidth) if ((mx + offsxy + bodyl + tooltip.offsetWidth) > bodyw) { mx = bodyw - offsxy - bodyl - tooltip.offsetWidth; if (mx < 0) mx = 0; }
    tooltip.style.left = (mx + offsxy + bodyl)+"px";
    tooltip.style.top  = (my + offsxy + bodyt)+"px";
  }
  with(tooltip) { ns4 ? visibility="show" : style.visibility="visible" }
  if (stick) document.onmouseup = hmhidePopup;
}
function hmhidePopup() {
  var tooltip = atooltip();
  ns4 ? tooltip.visibility="hide" : tooltip.style.visibility="hidden";
}
function atooltip(){
 return ns4 ? document.hmpopupDiv : ie4 ? document.all.hmpopupDiv : document.getElementById('hmpopupDiv')
}
popid_1766269953="<p><span style=\"color: #000000;\">Arial, normal text should be 11 points. May use bold and bold underlined for headers inside topics.<\/span><\/p>\n\r<p><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">In KTS, use Bold for titles, bold underlined indented for subtitles under that.<\/span><\/p>\n\r<p><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">Should always use neutral person (e.g. \"user\") instead of second hand.&nbsp; EXAMPLE:<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">(\"Typing in this field will bring up a list of unpaid purchase orders\" instead of \"When you start to type here, it will bring up a list of all unpaid purchase orders.\")<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">In the event of line-by-line notes, with no bullets, numbering or headings, use line spacing between lines. (example: formatting of this topic.) Also use this between bullets, numbering, etc. Would have title, full carriage return, detail, half space, detail, half space, etc. (I had a hard time finding this - it is an icon in the toolbar with two bars, a blue arrow, then two bars below it. Could not find a way to tell it to do this by default.)<\/span><\/p>\n\r<p><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">By default text should be far left aligned. May use indentations as needed.<\/span><\/p>\n\r<p><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">A topic for the browse of a screen will be appropriate between the overview and procedure topic if there are significant features available from the browse. (In most KTS chapters I have instead opted to put the browse in the overview.)<\/span><\/p>\n\r<p><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">Each normal chapter will have:<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">Overview - list of fields, buttons, detail (if they exist), then hotkeys. <\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 48px;\"><span style=\"color: #000000;\">- List fields in the order they appear on the screen, then buttons in the order they appear, then detail in order they appear, then hotkeys in the order of field hotkeys, button hotkeys, then detail hotkeys.<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">Hotkeys should be listed in the order of: <\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">i. Field hotkeys<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">ii. Button hotkeys<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">iii. Detail (grid) hotkeys<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">Procedure - step-by-step listing of how to use the item. May have extra notes at bottom<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">- Procedures may have links to chapters below it. The links should be the same name as the chapter\'s name. These chapters should be in the sequential order they are listed in the procedure chapter, and should immediately follow the procedures chapter.<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">Any longer procedures may be listed as a single item in the procedures, then have a link to a topic below the procedures, but above the troubleshooting.<\/span><\/p>\n\r<p style=\"margin: 0px 0px 0px 24px;\"><span style=\"color: #000000;\">May have troubleshooting topic as last topic in chapter.<\/span><\/p>\n\r<p><span style=\"color: #000000;\">&nbsp;<\/span><\/p>\n\r<p><span style=\"color: #000000;\">Note: This will not apply to some chapters, such as the key basics chapter, and the how to chapter. There may be other exceptions - this should just be a general guide.<\/span><\/p>\n\r<p>&nbsp;<\/p>\n\r<p>Pictures: Pictures should not be more than 500 pixels wide due to printing layout<\/p>\n\r<p>&nbsp;<\/p>\n\r<p>Topic color code:<\/p>\n\r<p> &nbsp; &nbsp; &nbsp; &nbsp;Red = Empty topic<\/p>\n\r<p> &nbsp; &nbsp; &nbsp; &nbsp;Aqua = Outdated<\/p>\n\r<p> &nbsp; &nbsp; &nbsp; &nbsp;Yellow = Under Construction<\/p>\n\r"
popid_733916404="<p>Initial Release<\/p>\n\r"
