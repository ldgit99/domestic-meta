var searchJs = 1;
$(document).ready(function() {
	//ê²ì ëª©ë¡ ìë¬¸ë³´ê¸° ë²í¼ í´ë¦­ì
//	var $btnOrigin = $('.srchResultListW > ul > li > .cont > .btnW > ul > li.viewOrigin > a');
	$(document).on('click', '.srchResultListW > ul > li > .cont > .btnW > ul > li.viewOrigin > a', function() {
//	$btnOrigin.on('click',function(){
		if(!$(this).parent().hasClass('on')){
			$(this).parent().addClass('on');
			$(this).next().slideDown('easeInOutQuart');
		}else{
			$(this).next().slideUp('easeInOutQuart', function(){
				$(this).parent().removeClass('on');
			});

		}
		return false;
	});

	//ê²ìëª©ë¡ ëª©ì°¨ê²ìì¡°í ë²í¼ í´ë¦­ì
	var $btnListView = $('.srchResultListW > ul > li > .cont > .btnW > ul > li.viewList > a');
	$btnListView.on('click',function(){
		$(this).parent().toggleClass('on');
		$(this).parent().parent().parent().next().slideToggle('easeInOutQuart');
		return false;
	});
	//í´ì¸íì ì§ í¼ì¹ê¸° ë²í¼
	$('.srchResultListW > ul > li > .cont > .title span.academicBtn').on('click',function(){
		$(this).toggleClass('on');
		$(this).parent().parent().parent().find('.divAcademicInfo').slideToggle(400);
		return false;
	});
	// ìì¸íì´ì§
	//ë¤êµ­ì´ë²ì­ í´ë¦­ ì
	$('.innerCont .additionalInfo .btnKakaoi').on('click',function(){
		if(!$(this).parent().next('.translateLangW').hasClass('on')){
			$(this).parent().next('.translateLangW').addClass('on');
			$(this).parent().next('.translateLangW').show();
			//ê¸°ì¡´ ì´ë¡ íì¤í¸ ìë³´ì´ëë¡
			$(this).parent().siblings('.text').addClass('hide');
		}else{
			$(this).parent().next('.translateLangW').removeClass('on');
			$(this).parent().next('.translateLangW').hide();
			$(this).parent().siblings('.text').removeClass('hide');
		}
		return false;
	});
	// ë²ì­ ì¸ì´ì í
	$('.translateTopArea .choiceLang > a').on('click',function(){
		$(this).parent().toggleClass('on');
		$(this).parent().siblings().removeClass('on');
		return false;
	});

	// ë²ì­ ì¸ì´ì í
	$('.translateTopArea .choiceLang .langList ul li > a').on('click',function(){
		$(this).parent().addClass('on').siblings().removeClass('on');
		$(this).parent().parent().parent().parent().find("a span.txtInner").text($(this).text());
		$('.translateTopArea .choiceLang').removeClass('on');

		return false;
	});
	//ìë¬¸ë³´ê¸° ë²í¼
	$('.searchDetail .btnBunch > .btnBunchL > ul > li.viewOrigin > a').on('click',function(){
		$(this).parent().toggleClass('on');
		$(this).next().slideToggle(400);
		return false;
	});
	// ì´ë¡ë³´ê¸° ë²í¼
	$('.srchResultListW > ul > li > .cont > .btnW > ul > li.viewAbstract > a').on('click',function(){
		$(this).parent().toggleClass('on');
		$(this).next().slideToggle(400);
		return false;
	});

	//ëë³´ê¸°-ìì§ìì¸
	$('.searchDetail .infoDetail .moreView').on('click',function(){
		if(!$(this).parent().hasClass('on')){
			$(this).parent().addClass('on');
			$(this).siblings().find('.off').removeClass('off').addClass('on');
		}else{
			$(this).parent().removeClass('on');
			$(this).siblings().find('.on').addClass('off').removeClass('on');
		}
		return false;
	});

	//ëë³´ê¸°-ë¶ê°ì ë³´
	$('.innerCont > .additionalInfo > div > .moreView').on('click',function(){
		var $content = $(this).parent().find('.text');
		$(this).toggleClass('on');
		$content.toggleClass('off');
		return false;
	});

	//ëë³´ê¸°-ë¶ìì ë³´
	var $analysis1 = $('.innerCont > .analysisInfo .analysisContW .moreView'); /*íì©ëë¶ì*/
	$analysis1.on('click',function(){
		if(!$(this).hasClass('on')){
			$(this).addClass('on');
			$(this).siblings().find('.off').removeClass('off').addClass('on');
			$(this).prev().removeClass('off').addClass('on');

			for (var i = 0; i < Highcharts.charts.length; i++) {
				if(Highcharts.charts[i]) Highcharts.charts[i].reflow();
			}
		}else{
			$(this).removeClass('on');
			$(this).siblings().find('.on').removeClass('on').addClass('off');
			$(this).prev().removeClass('on').addClass('off');
		}
		return false;
	});

	//ëë³´ê¸°-ì°ê´ìë£
	$('.innerCont > .relation > div > .moreView').on('click',function(){
		var $content = $(this).parent().find('.lectureW');
		$(this).toggleClass('on');
		$content.toggleClass('off');
		return false;
	});
	//ëë³´ê¸°-ì°ê´ìë£
	$('.innerCont .otherThesis .moreView').on('click',function(){
		var $content = $(this).parent().find('.relationList');
		$content.toggleClass('off');
		return false;
	});
	// ëë³´ê¸°-ì¨ë¼ì¸ ëìì ë³´
	$('.onlineInfo .txtW > .moreView').on('click',function(){
		var $content = $(this).parent().find('.txt');
		$(this).toggleClass('on');
		$content.toggleClass('off');
		return false;
	});

	// ëë³´ê¸°-ì¸ì©ì ë³´
	$('.quotation .moreView').on('click',function(){
		var $content = $(this).parent().find('div');
		$(this).toggleClass('on');
		$content.toggleClass('off');
		return false;
	});

	//ë¶ìì ë³´ í­ í´ë¦­ì
	var $analysisTab = $('.innerCont > .analysisInfo > ul > li > a');
	var $tabCont = $('.innerCont > .analysisInfo .analysisContW > div');
	var $topicTab = $('.analysisCont .thesisTopicTop > ul > li > a');
	var $topicCont = $('.thesisTopic .thesisTopicCont');
	var tabIdx = 0;
	var topicIdx = 0;

	$analysisTab.on('click',function(){
		tabIdx = $analysisTab.index($(this));
		$(this).parent().addClass('on').siblings().removeClass('on');
		$tabCont.eq(tabIdx).addClass('on').siblings().removeClass('on');
		return false;
	});

	//ë¼ë¬¸ Analysis ì£¼ì  í­
//	$topicTab.on('click',function(){
	$(document).on('click','.analysisCont .thesisTopicTop > ul > li > a',function(){
		topicIdx = $topicTab.index($(this));
		$(this).parent().addClass('on').siblings().removeClass('on');
		$topicCont.eq(topicIdx).addClass('on').siblings().removeClass('on');
		return false;
	});

	//ì°êµ¬ì ì£¼ì ë¶ì ë¼ë¬¸ í­
//	$('.researchTopicCont .thesisList > ul > li > a').on('click',function(){
	$(document).on('click','.researchTopicCont .thesisList > ul > li > a',function(){
		$(this).parent().addClass('on').siblings().removeClass('on');
		return false;
	});

	// íì ì§ Left Menu
	// tab
	$(window).on('load',function(){
		$('.leftMenuJournal .leftMenuList > ul > li').each(function(){
			if($(this).hasClass('on')){
				$(this).children('ul').show();
			}
		});
	});

	$('.leftMenuJournal .leftMenuList > ul > li > a').on('click',function(){
		$(this).parent().addClass('on');
		$(this).next().slideToggle(300);
		return false;
	});

	$(document).on('click', '.leftMenuJournal .leftMenuList > ul > li > ul > li > a', function() {
		$('.leftMenuJournal .leftMenuList > ul > li > ul > li').removeClass('on');
		$(this).parent().addClass('on');
//		return false;
	});

	//íì ì§ë³ ê²ì
	$('.acdmSrchListW .cateList li a').on('click',function(){
		if($(this).parent().find('ul').length>0){
			$(this).parent().toggleClass('open');
			$(this).siblings('ul').slideToggle(300);
			return false;
		}
	});

	//ê³µì íê¸° ë²í¼ í´ë¦­
	$('.btnShare1 a').not('.a2a_button_facebook, .a2a_button_twitter').on('click',function(){
		$(this).next().slideToggle(400);
		return false;
	});
	//ìì­ì¸ í´ë¦­ì ë«í
	$('#wrap').click(function(evt){
		if(!$('.btnShare1 div').has(evt.target).length){
			$('.btnShare1 div').slideUp(300);
		}
	});


	//ë¨íë³¸ ëìë¦¬ì¤í¸
	//ëìë¦¬ì¤í¸ 7ê° ì´ìì¼ ê²½ì°ìë§ ì¢ì° íì´í íì
	$('.bookInfo .divBookList').each(function(){
		if($(this).find('li').length>7){
			$(this).children('.controller').show();
		}
	});

	//ëì ì¬ë¼ì´ë
	var $next = $('.bookInfo .divBookList .next');
	var $prev = $('.bookInfo .divBookList .prev');
	var $ul = $('.bookInfo .divBookList > div ul');
	var bookWidth = $('.bookInfo .divBookList > div ul li').outerWidth(true);

	//ë¤ìë²í¼ í´ë¦­
	$next.on('click',function(){
		var $li = $(this).prev().find('li');
		var $ul = $(this).prev().children('ul');
		bookWidth = $('.bookInfo .divBookList > div ul > li').outerWidth(true);
		if(!$ul.is(':animated')){
			$ul.animate({'left':-bookWidth},600,function(){
				$li.first().appendTo($ul);
				$ul.css('left','0');
			});
		}
		return false;
	});
	//ì´ì ë²í¼ í´ë¦­
	$prev.on('click',function(){
		var $li = $(this).next().find('li');
		var $ul = $(this).next().children('ul');
		bookWidth = $('.bookInfo .divBookList > div ul > li').outerWidth(true);
		if(!$ul.is(':animated')){
			$li.last().prependTo($ul);
			$ul.css('left',-bookWidth);
			$ul.animate({'left':'0'},600);
		}
		return false;
	});

	// 2021.10.18 ì¶ê°
	// ì¶ì² ë¦¬ì¤í¸ íë¨ ëê·¸ë¼ë¯¸ í´ë¦­
	$(document).on("click",".recomlistW > .menu > li > a", function(e){
		e.preventDefault();
		let num = $(this).parent().index();
		$(this).parents(".menu").children("li").removeClass("on");
		$(this).parent().addClass("on");
		$(this).parents(".recomlistW").children(".list").animate({"margin-left": (num * -110) + "%"},500);
	});

	// ì¶ì² ë¦¬ì¤í¸ ë°ì¤ ì ê³  ì´ê¸°
	$(".recomToggle").on("click",function(e){
		e.preventDefault();


		if($(this).attr("title")=="ì´ê¸°"){

			$(this).attr("title","ì ê¸°")
			$(this).children("img").attr("src","/search/images/recommendClose_btn.png");
			$(this).parents(".recombox").children(".recomlistW").animate({"height":"305px","padding":"14px 17px"},500);
		}else{

			$(this).attr("title","ì´ê¸°")
			$(this).children("img").attr("src","/search/images/recommendOpen_btn.png");
			$(this).parents(".recombox").children(".recomlistW").animate({"height":0,"padding":"0 17px"},500);
		}

	});
	// íì©ë ëì ìë£ ì¶ì² ë¦¬ì¤í¸ ìì¸íë©´
	$(".recomMoreBtn").on("click",function(e){
		e.preventDefault();
		// ê²ìì ë°°ê²½ ëì´ê°, ê°ë¡ê° ëì ì¼ë¡ ì§ì , rightê° ê³ì°
		$(".recomMoreList").css({"height":$("body").height(), "width":$("body").width(), "right" : ($("body").width()-$("#divContent").width())/-2,"top":-$(this).parent().offset().top});
		$(".recomMoreList").stop().fadeIn();
	});

	$(".moreListClose").on("click",function(e){
		e.preventDefault();
		$(".recomMoreList").stop().fadeOut();
	});

		// sjr
	$(".sjrW .infoW a").on("click", function(e){
		e.preventDefault();
		if($(this).parents(".infoW").hasClass("on")){
			$(this).parents(".infoW").removeClass("on")
		}else{
			$(this).parents(".infoW").addClass("on")
		}
	});


	// ë´ RISSíµê³ ë§ì´ ì½ì ì ì
	$(".readStats > .readStatsCont1 > .colorTile > ul > li > a").on("click",function(e){
		e.preventDefault();
		// ê²ìì ë°°ê²½ ëì´ê°, ê°ë¡ê° ëì ì¼ë¡ ì§ì , rightê° ê³ì°
		$(".readStatsList").css({"height":$("body").height(), "width":$("body").width()+7, "right" : ($("body").width()-$("#divContent").width())/-2, "top":-$(this).offsetParent().offset().top});
		$(".readStatsList").stop().fadeIn();
	});

	$(".readStatsList .closeBtn").on("click",function(e){
		e.preventDefault();
		$(".readStatsList").stop().fadeOut();
	});

	//ê²ìí¨ì¯ ì´ê³ ë«ê¸°
	$('.articleToggleBtn').click(function(){
		if($(this).hasClass('on')){
			$(this).removeClass('on');
			$(this).attr("title","í¼ì¹ê¸°")
			$(this).text('í¼ì¹ê¸°')
			$(this).prev('.contList').removeClass('on');
			$(this).prev('.contList').mCustomScrollbar({theme:"dark-3"});
		}else{
			$(this).addClass('on');
			$(this).attr("title","ë«ê¸°")
			$(this).text('ë«ê¸°')
			$(this).prev('.contList').addClass('on');
			$(this).prev('.contList').mCustomScrollbar('destroy');

		}
		return false;
	});
});



var ButtonSet = {
    ddodDownloadSubmit : function(controlNo, imageFormat, ddodFlag) {
         with(document.f) {
             control_no.value = controlNo;
             fulltext_kind.value = imageFormat;
             loginFlag.value=1;
             ddodDownloadSubmit(ddodFlag);
             loginFlag.value='';
         }
     },
     fulltextDownload : function(controlNo, matType, matSubtype, imageFormat, tGubun) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             p_submat_type.value = matSubtype;
             fulltext_kind.value = imageFormat;
             t_gubun.value = tGubun;
             content_page.value = '';//ëª©ì°¨ê²ìì¡°í íì´ì§ê° ì´ê¸°í
             fulltextDownload();
         }
     },
     contentFulltextDownload : function(controlNo, matType, matSubtype, imageFormat, tGubun, contentPage) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             p_submat_type.value = matSubtype;
             fulltext_kind.value = imageFormat;
             t_gubun.value = tGubun;
             content_page.value = contentPage;
             fulltextDownload();
         }
     },
    urlDownload : function(urltype, controlNo, matType, matSubtype, imageFormat, tGubun) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             url_type.value = urltype;
             urlDownload(urltype);
         }
     },
     publicUrlDownload : function(urltype, controlNo, matType, matSubtype, imageFormat, orgCode, tGubun) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             url_type.value = urltype;
             mingan_org_storage.value = orgCode;
             publicUrlDownload(urltype);
         }
     },
     checkKyoboUrl: function(urlTypeW, urlTypeM, controlNo, matType, academicUserYn, isLogin) {

   	  if(isLogin == "2") {
	  	    	if(academicUserYn == "Y") {
		    		ButtonSet.kyoboUrlDownload(urlTypeM, controlNo, matType, '', '', '');
		    	} else {
		    		ButtonSet.kyoboUrlDownload(urlTypeW, controlNo, matType, '', '', '');
		    	}
   	  } else {
	      	    if(confirm('\'ì¤ì½ë¼\' ë¯¸êµ¬ë ê¸°ê´ ì´ì©ìë ì¤í 4ìë¶í° ìµì¼ ì¤ì  9ìê¹ì§\nRISS ê°ì¸ ë¡ê·¸ì¸ì íµí´ ë¬´ë£ë¡ ìë¬¸ë³´ê¸°ë¥¼ ì¬ì©íì¤ ì ììµëë¤.\n\nê°ì¸ë¡ê·¸ì¸ì¼ë¡ ì í íìê² ìµëê¹?')) {
	    	    	if(academicUserYn == "Y") {
	    	    		ButtonSet.kyoboUrlDownload(urlTypeM, controlNo, matType, '', '', '');
	    	    	} else {
	    	    		ButtonSet.kyoboUrlDownload(urlTypeW, controlNo, matType, '', '', '');
	    	    	}
	    	    } else {
	    	    	ButtonSet.urlDownload(urlTypeW, controlNo, matType, '', '', '');
	    	    }
	  	  }

     },
     kyoboUrlDownload : function(urltype, controlNo, matType, matSubtype, imageFormat, tGubun) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             url_type.value = urltype;
             kyoboUrlDownload(urltype);
         }
     },
     memberUrlDownload : function(orgcode, urltype, controlNo, matType, matSubtype, imageFormat, tGubun) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             url_type.value = urltype;
             memberUrlDownload(urltype, controlNo, orgcode);
         }
     },
     publicMemberUrlDownload : function(orgcode, urltype, controlNo, matType, matSubtype, imageFormat, tGubun) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             url_type.value = urltype;
             publicMemberUrlDownload(urltype, controlNo, orgcode);
         }
     },
     overFulltextDownload : function(targetUrl, dbname, controlNo, matType) {
         with(document.f) {
             control_no.value = controlNo;
             p_mat_type.value = matType;
             overFulltextDownload(targetUrl, dbname);
         }
     },
     memberFulltextDownlod : function(viewcode, orgcode, p_mat_type)
     {
       var x=window.open("/search/download/FullTextDownload.do?viewcode="+viewcode+"&orgcode="+orgcode+"&p_mat_type="+p_mat_type+"&loginFlag=1","FulltextDownload","status=0,toolbar=0,Titlebar=0,width=840,height=680,resizable=1");
     }
 }

function alertFullTextLayer(controlNo, orgStorage, minganOrgStorage, urlType, minganCd, gubun){
	$('#f input[name=control_no]:hidden').val(controlNo);
	$('#f input[name=org_storage]:hidden').val(orgStorage);
	$('#f input[name=fulltmingan_org_storage]:hidden').val(minganOrgStorage);
	$('#f input[name=url_type]:hidden').val(urlType);
	$('#f input[name=mingan_cd]:hidden').val(minganCd);
	$('#f input[name=gubun]:hidden').val(gubun);
	$('#alertFulltextLayer').css("display","");
}

function openFulltextLayer(){
	var controlNo = $('#f input[name=control_no]:hidden').val();
	var orgStorage = $('#f input[name=org_storage]:hidden').val();
	var minganOrgStorage = $('#f input[name=fulltmingan_org_storage]:hidden').val();
	var urlType = $('#f input[name=url_type]:hidden').val();
	var minganCd = $('#f input[name=mingan_cd]:hidden').val();
	var gubun = $('#f input[name=gubun]:hidden').val();

	openFulltext(controlNo, orgStorage, minganOrgStorage, urlType, minganCd, gubun);
	$('#alertFulltextLayer').css("display","none");
}

function openFulltext(aControlNo, orgStorage, minganOrgStorage, urlType, minganCd, gubun) {
    var form=document.f;
    //form.action="/PopupLogin.do?loginFlag=1";
    //form.action="/LoginRedirect.do";
//    form.loginFlag.value="1";
//    form.url_type.value=urlType;

    //var pars=jQuery(form).serialize();

    var pars = "control_no=" + aControlNo + "&org_storage=" + orgStorage + "&mingan_org_storage=" + minganOrgStorage + "&url_type=" + urlType + "&gubun="+gubun;


    var cw=700;
    var ch=700;
	var sw=screen.availWidth;
	var sh=screen.availHeight;

	  //ì´ ì°½ì í¬ì§ì
	var px=(sw-cw)/2;
	var py=(sh-ch)/2;
	var option = "";


	// PDF, Dcollecton ìë£ì¸ìë ì ì²´íë©´ì¼ë¡ í¸ì¶
	if(minganCd == "90" || minganCd == "91" ) {
		option = "scrollbars=no, toolbar=no, resizable=1, status=no, location=no, menu=no, Width="+cw+", Height="+ch+",left="+px+",top="+py;

//		else {
//			option = "";
//		}
	}
//	else {
//		option = "";
//	}

	if((minganCd == "07" && gubun == "KYOBO")) {
			pars += "&loginFlag=1";
	}

	var url = "/search/download/openFullText.do?"+pars;

	var f = window.open(url, "_blank", option);

}

/*
 * ëª©ì°¨ê²ìì¡°í
 */
function contentView(target, key, matType, matSubtype, imageFormat, page){
    //znAll, znTitle, znKtoc
    var frm = document.ReSearch;
    var text = frm.query.value;
    var texts = frm.queryText.value;
    var target_g = target.substring(1);

    jQuery.ajax({
        type: "POST",
        url: "/search/detail/QuickContentAjax.do",
        dataType : "html",
        data: {target : target_g ,
        	control_no : key,
        	p_mat_type : matType,
        	p_submat_type : matSubtype,
        	fulltext_kind : imageFormat,
        	page : page,
        	query : text,
        	queryText : texts
        	},
        success : function(html){
                    if(html.indexOf("ì ìí ë¤ì ì´ì©í´ì£¼ì¸ì.") == -1) document.getElementById(target).style.display = "block";
                    else document.getElementById(target).style.display = "none";

                    jQuery("#"+target).html(trim(html));
                },
        error: function(result){
                    document.getElementById(target).style.display = "none";
                    jQuery("#"+target).html("");
                    alert("ì¡°íì ì¼ìì ì¸ ë¬¸ì ê° ë°ìíììµëë¤.\në¤ì ìëí´ ì£¼ì¸ì.");
                }
    });
}

function fulltextListView(target,key){
	var targetNum = target.replace('A_','');
	var className = $('#viewOrigin_'+targetNum).attr('class');

	if(className.indexOf("on") == -1){
	    jQuery.ajax({
	        type: "POST",
	        url: "/search/detail/AuthWileyAjax.do",
	        dataType : "html",
	        data: {
	        	control_no : key
	        	},
	        	success : function(html){
	        		document.getElementById(target).style.display = "block";
	        		jQuery("#"+target).html(trim(html));
	            },
	            error: function(result){
	                document.getElementById(target).style.display = "none";
	                jQuery("#"+target).html("");
	                alert("ì¡°íì ì¼ìì ì¸ ë¬¸ì ê° ë°ìíììµëë¤.\në¤ì ìëí´ ì£¼ì¸ì.");
	            }
	    });
	}else{
		document.getElementById(target).style.display = "none";
		jQuery("#"+target).html(trim(html));
	}

}

function preView(target,key,gubun){
	var targetNum = target.replace('preViewInfo_','');
	var className = $('#viewAbstract_'+targetNum).attr('class');

//	if(className.indexOf("on") == -1){
	    jQuery.ajax({
	    	type: "POST",
	        url: "/search/detail/AbstractSelectAjax.do",
	        dataType : "html",
	        data: {
	        	control_no : key,
	        	p_mat_type : gubun
	        	},
	        	success : function(html){
	        		if(className.indexOf("on") == -1) document.getElementById(target).style.display = "block";
	                else document.getElementById(target).style.display = "none";

	                jQuery("#"+target).html(trim(html));
	            },
	            error: function(result){
	                document.getElementById(target).style.display = "none";
	                jQuery("#"+target).html("");
	                alert("ì¡°íì ì¼ìì ì¸ ë¬¸ì ê° ë°ìíììµëë¤.\në¤ì ìëí´ ì£¼ì¸ì.");
	            }
	    });
//	}else{
//		document.getElementById(target).style.display = "none";
//		jQuery("#"+target).html(trim(html));
//	}
}

// ëª©ì°¨ DBì¡°í
// UT_BIB_DESC_DIVIDE
function tocView(target, key, page){
    var frm = document.ReSearch;
    jQuery.ajax({
        type: "POST",
        url: "/search/detail/tocAjaxView.do",
        dataType : "html",
        data: {
        	target : target,
        	control_no : key,
        	page : page
        	},
        success : function(html){
                    if(html.indexOf("ì ìí ë¤ì ì´ì©í´ì£¼ì¸ì.") == -1) document.getElementById(target).style.display = "block";
                    else document.getElementById(target).style.display = "none";

                    jQuery("#"+target).html(trim(html));
                },
        error: function(result){
                    document.getElementById(target).style.display = "none";
                    jQuery("#"+target).html("");
                    alert("ì¡°íì ì¼ìì ì¸ ë¬¸ì ê° ë°ìíììµëë¤.\në¤ì ìëí´ ì£¼ì¸ì.");
                }
    });
}

function chkKyoboUrl(urlTypeW, urlTypeM, academicUserYn, isLogin, aControlNo, orgStorage, minganOrgStorage, minganCd) {

	var strUrlType = "";
	var strGubun = "";

	if(isLogin == "2") {
		if(academicUserYn == "Y") {
    		strUrlType = urlTypeM;
    		strGubun = "KYOBO";
    	} else {
    		strUrlType = urlTypeW;
    		strGubun = "KYOBO";
    	}
	} else {
	    if(confirm('ë¯¸êµ¬ë ê¸°ê´ì ì´ì©ìë ì¤í 4ìë¶í° ìµì¼ ì¤ì  9ìê¹ì§\nRISS ê°ì¸ ë¡ê·¸ì¸ì íµí´ ë¬´ë£ë¡ ìë¬¸ë³´ê¸°ë¥¼ ì¬ì©íì¤ ì ììµëë¤.\n\nê°ì¸ë¡ê·¸ì¸ì¼ë¡ ì í íìê² ìµëê¹?')) {
	    	if(academicUserYn == "Y") {
	    		strUrlType = urlTypeM;
	    		strGubun = "KYOBO";
	    	} else {
	    		strUrlType = urlTypeW;
	    		strGubun = "KYOBO";
	    	}
	    } else {
	    	strUrlType = urlTypeW;
	    }
	}


	openFulltext(aControlNo, orgStorage, minganOrgStorage, strUrlType, minganCd, strGubun);

}

//TTSìì±ë£ê¸°
function ttsPopupView(aControlNo){
	var targetName = 'ttsPopup';
	var url = "/search/detail/ttsView.do?aControlNo="+aControlNo;
    var win = window.open('',targetName, 'width=1200,resizable,scrollbars,location');
    win.location.href = url;
    win.focus();
}

function newTtsPopupView(control_no, p_mat_type, s_mat_type, mat_subtype_cd, imageFormat ){
	//http://dcollection.korea.ac.kr/jsp/common/SvcOrgDownLoad.jsp?insCode=211009&item_id=000000127810
	/*
    $.ajax({
        url : 'http://tts.riss.kr/custom/external-resources',
        type : 'POST',
        data : JSON.stringify({'externalId': "http://dcollection.korea.ac.kr/jsp/common/SvcOrgDownLoad.jsp?insCode=211009&item_id=000000127810",}),
        contentType: 'application/json',
        cache : false,
        success : function(data) {
            console.log('data : ', data);
            window.open('http://tts.riss.kr/view/sd;streamdocsId=' + data.streamdocsId);
        }
    });
    */
	var uri = "";
	jQuery.ajax({
        type: "POST",
        url: "/search/download/newTtsView.do",
        dataType : "html",
        data: {
        	control_no : control_no,
        	p_mat_type : p_mat_type,
        	s_mat_type : s_mat_type,
        	mat_subtype_cd : mat_subtype_cd,
        	imageFormat : imageFormat
        },
        //data:jQuery(document.f).serialize(),
        success : function(html){
        	uri = html;
        	if(uri=='ìì± ìë¹ì¤ ëìì´ ìëëë¤.'){
        		alert(uri);
        		location.reload();
        	}else{

        		//FullTextDownloadControllerìì ì²ë¦¬(ì¤ë¥ë°ìì ì¶ê° ë¡ì§ ê²í )

        		//uri = uri.replace('https://','http://');
        		uri = uri.replace('DcLoOrgPer','SvcOrgDownLoad');
        		uri = uri.replace('sItemId','item_id');
        		uri = uri.replace('/common/orgView/','/jsp/common/SvcOrgDownLoad.jsp?item_id=');
        		uri = uri.replace(';','');

        		window.open('https://ttsn.riss.kr/custom/external-resources/view.do?externalId=' + encodeURIComponent(uri));

        		/*
        		  ìì±ë£ê¸° í´ë¦­ì ì´ë²¤í¸ íìì°½
                */
                /*
        		if(new Date() >= new Date('2022-08-10 00:00:00') && new Date() <= new Date('2022-08-26 23:59:59')){
        			if (getCookie("pop_alert_220811") != "done" ) {
        				var pTop=50;
        		        var pLeft=380;
        		        var pWidth=624;
        		        var pHeight=882+26;
        		        window.open("http://www.riss.kr/main/etc/PopupEventView.do?survey_gubun=20220810", "popup_20220810", "top="+pTop+",left="+pLeft+",width="+pWidth+",height="+pHeight+",status=no,menubar=no,resizable=yes,scrollbars=yes");

        			}
        		}
        		*/

        	}
        },
        error: function(result){
        	//jQuery("#"+target).html("");
            alert("ì¡°íì ì¼ìì ì¸ ë¬¸ì ê° ë°ìíììµëë¤.\në¤ì ìëí´ ì£¼ì¸ì.");
        }
    });
}



/*
**  íë©´ ì ì¤ìì POPUP WINODOW OPEN(POST ë°©ì)
*/
function fnOpenCenterWinPostResize(form, name, w, h, scroll, resize) {

	var wl = (window.screen.width/2) - ((w/2) + 10);
	var wt = (window.screen.height/2) - ((h/2) + 50);

	var option = "status=no,height="+h+",width="+w+",resizable="+resize+",left="+wl+",top="+wt+",screenX="+wl+",screenY="+wt+",scrollbars="+scroll;
	commonPopWin = window.open( '', name, option );
	form.target = name;
	//form.action = url;
	form.submit();
	commonPopWin.focus();
	return commonPopWin;
}

//ì«ì§ë§ ìë ¥íëë¡(ë°íë)
function onlyNumber() {
	if ((event.keyCode < 48) || (event.keyCode > 57) ) {
		event.returnValue = false;
	}
}

//ìí¸ëì°¨ íì
function OpenOrder(ctrl_no, type, v_ctrl_no){
    var targetName = 'order';
    if (!v_ctrl_no) v_ctrl_no = "";
    //2013.8.12 ì²­ì¬ ì´ì ì¼ë¡ ì ê· ì ì²­ ì í
    //alert("KERIS ì ì°ì¼í° ì´ì ì ë°ë¼ 8. 14(ì) 18:00ë¶í° 8. 30(ê¸) 09:00ê¹ì§ ì ê· ì ì²­ì´ ë¶ê°ë¥í©ëë¤.\n8. 23(ê¸) 18:00ê¹ì§ ì§í ì¤ì¸ í¸ëì­ìì ì¢ë£ ì²ë¦¬íì¬ ì£¼ìê¸° ë°ëëë¤.\nìë¹ì¤ ì´ì©ì ë¶í¸ì ëë ¤ ì£ì¡í©ëë¤.");
    //return;
    var win = window.open('/order/OrderForm.do?requestType=requestPanel&loginFlag=1&ctrl_no='+ctrl_no+'&type='+type+'&v_ctrl_no='+v_ctrl_no+'&conType=real',targetName,"status=0,toolbar=0,Titlebar=0,scrollbars=1,resizable=1,width=838px,height=550px");
    win.focus();
}

// NII íì
function OpenOrderNII(utno){

    //2013.8.12 ì²­ì¬ ì´ì ì¼ë¡ ì ê· ì ì²­ ì í
    //alert("KERIS ì ì°ì¼í° ì´ì ì ë°ë¼ 8. 14(ì) 18:00ë¶í° 8. 30(ê¸) 09:00ê¹ì§ ì ê· ì ì²­ì´ ë¶ê°ë¥í©ëë¤.\n\nìë¹ì¤ ì´ì©ì ë¶í¸ì ëë ¤ ì£ì¡í©ëë¤.");
    //return;
    var targetName = 'orderNII';

    var win = popupWindow('/order/OrderForm.do?loginFlag=1&utno='+utno,
            targetName,
            "820", "550");
    win.focus();
}

function riss_fsearch_ddod(url, db, dbId, an, dpName) {
	var form = document.popupFulltextForm;
	var name = "resourceView";
	var w=1075;
	var h=675;
	var scroll="yes";
	var resize="yes";

	form.action = "<c:url value='/fsearch/popup/ResourceView.do'/>";
	form.url.value = url;
	form.dbName.value = db;
	form.dbId.value = dbId;
	form.an.value = an;
	form.dbNameDpShort.value = dpName;

	fnOpenCenterWinPostResize(form, name, w, h, scroll, resize);
}

function riss_fsearch_fric(url, db) {
	var form = document.popupFricForm;
	var name = "fricLinkView";
	var w=880;
	var h=650;
	var scroll="yes";
	var resize="yes";

	form.action = url.replace("http://www.riss.kr","").replace("https://www.riss.kr","")+"&loginFlag=1";
	form.db.value = db;

	fnOpenCenterWinPostResize(form, name, w, h, scroll, resize);
}

function riss_fsearch_dds(isFCopyAuth,url) {

	if(isFCopyAuth != "Y"){
		alert("í´ì¸ì ìì ë³´ìë¹ì¤ ë³µì¬ì ì²­ ê¶íì´ ë¶ì¡±íì¬ ì´ì©íì¤ ì ììµëë¤.");
		return false;
	}else{
		var form = document.popupFricForm;
		var name = "ddsLinkView";
		var w=880;
		var h=650;
		var scroll="yes";
		var resize="yes";

		form.action = url.replace("http://www.riss.kr","").replace("https://www.riss.kr","")+"&loginFlag=1";
		form.db.value = db;

		fnOpenCenterWinPostResize(form, name, w, h, scroll, resize);
	}
}

//í´ì¸ì ì ë³µì¬ì ì²­
function setRissFCopyBtn(loginYn,ctrlNo,issn,year,infoUrl,rowCnt){

	if(loginYn == "Y" && issn != null && issn != ""){

		$.ajax({
			type: "POST",
			url: "/search/getRissFCopyAjax.do",
			data: {
				ctrlNo: ctrlNo,
				issn: issn,
				pubDt : year,
				linkUrl : infoUrl
			},
			dataType: "json",
			success: function(data){

				if(data != null) {
					var obj = JSON.parse(data);
					var rissCopyBtn = $(".rissCopy_" + rowCnt);
					var html = "";
					var linkUrl = obj.linkUrl;
					var isFCopyAuth = obj.isFCopyAuth;
					var type = obj.type;

					//console.log( "==================================" );
					//console.log( "linkUrl:"+linkUrl );
					//console.log( "isFCopyAuth:"+isFCopyAuth );
					//console.log( "type:"+type );
					//console.log( "==================================" );

					if(linkUrl != null && linkUrl != ''){

						if(isFCopyAuth == "Y"){
							html = "<a href=\"javascript:void(0);\" onclick=\"javascript:riss_fsearch_dds('" + isFCopyAuth + "','" + linkUrl + "');\">ë³µì¬/ëì¶ì ì²­</a>";
						}
						rissCopyBtn.css("display","block");
						rissCopyBtn.html(html);

						//íì ì§ ê¶í¸ìì¥ ë²í¼ì¶ë ¥ì ì´ ì¶ê°
						var btnR = rissCopyBtn.parent('.btnR');
						if(btnR.length > 0){
							btnR.css("display","block");
						}
					}
				}
			},
			error: function(xhr, status, error) {
			}
		});
	}
}

function riss_fsearch_fulltext(url, db, dbId, an, dpName) {
	var form = document.popupFulltextForm;
	var name = "resourceView";
	var w=1075;
	var h=675;
	var scroll="yes";
	var resize="yes";

	/*
	//Http,Https ì´ìë¡ publication ê²ìì ì¡ì¤ì½ìì url ë³ê²½ì íê¸° íë¤ì´ RISSìì ë³ê²½íë¤. - ì¡ì¤ì½ ê¹ì±í ë¶ì¥ ìì²­
	String.prototype.startsWith=function(str){ //IEë startsWithë¥¼ ì§ìíì§ ìì ì§ì  ëªì
		if(this.length<str.length){return false;}
		return this.indexOf(str) ==0;
	}
	var protocol = location.protocol;
	if(protocol.startsWith("http:") && url.startsWith("https:")){
		url = url.replace('https:', 'http:');
	}else if(protocol.startsWith("https:") && url.startsWith("http:")){
		url = url.replace('http:', 'https:');
	}*/

	form.action = "/fsearch/popup/ResourceView.do";
	form.url.value = url;
	form.dbName.value = db;
	form.dbId.value = dbId;
	form.an.value = an;
	form.dbNameDpShort.value = dpName;

	fnOpenCenterWinPostResize(form, name, w, h, scroll, resize);
}

function fnGoNewestBest() {
	document.location = "/NewestBest.do"
}
