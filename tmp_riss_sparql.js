$(document).ready(function(){
	
//	$.getJSON("area.jsp", function(msg){		
//		$.each(msg, function(id, value){
//			$("#area").append('<option value="' + id + '">' + value + '</option>');			
//		});
//	});	
//	
//	$.getJSON("sparqlSampleList.jsp", function(msg){
//		$("#sparqllist").empty();
//		var i = 0;
//		$.each(msg, function(id, value){
//			$("#sparqllist").append('<option value="' + id + '">' + value + '</option>');
//			i++;
//		});		
//		$("#sparqllist").attr("size", i);
//	});	
	
	$("#schxml").click(function(){	                
		$.blockUI({ message: "<img src='images/default/loading.gif'/>" });
                            var qryValue = $("#userquary").val();
                            var flag = $('#flag').val();                            
		if( qryValue.length == 0 ){
			return;
		}
		var type = $("#type").val();
                doTimer();
		$.ajax({ 
			type:'GET',
			//url:'sparql'+type+'.jsp',
			//data: ( {"qry" : qryValue} ),
			url:'sparql',
                        dataType:"text",
			data: ( {"query" : qryValue, "type":type, "flag":flag} ),
			success:function(msg){		
				if( type == 'Xml'){    
					if (window.ActiveXObject){
                                            //msg = msg.xml;
                                            //msg = (new XMLSerializer()).serializeToString(msg);
                                        }else{ // code for Mozilla, Firefox, Opera, etc.
                                            //msg = (new XMLSerializer()).serializeToString(msg); 
                                        }
                                        //msg = (new XMLSerializer()).serializeToString(msg); 
					$("#schxmlview").html("<textarea>"+msg+"</textarea>");					
				}else if( type == 'Html' ){					
					$("#schxmlview").html(msg);					
				}else if( type == 'Json' ){		
					$("#schxmlview").html("<textarea>"+msg+"</textarea>");			
				}
			},
			complete: function() { 
				$.unblockUI();
                                stopCount();
                        }
		});
		//$.unblockUI();
	});
	
	$("#area").change(function (){
		$.getJSON("sparqlSampleList.jsp", {"area":$("#area").val()}, function(msg){
			$("#sparqllist").empty();
			var i = 0;
			$.each(msg, function(id, value){
				$("#sparqllist").append('<option value="' + id + '">' + value + '</option>');
				i++;
			});		
			$("#sparqllist").attr("size", i);
		});		
	});
	
	// ì¤íí´ ìí ì í ì¿¼ë¦¬ ë³´ì¬ì£¼ê¸°
	$("#sparqllist").change(function(){
		var id = $("#sparqllist").val();
		$.ajax({
			type : 'GET',
			url : "sparqlSample.jsp",
			data : "id="+id,
			success:function(msg){			
				$("#userquary").val(msg);				
			}
		});
		
	});
	
	// ê²ìê²°ê³¼ ë¤ì´ë¡ë
	$("#schxmldown").click(function(){
		var type = $("#type").val();
		document.downloadSparqlForm.action = 'sparql';
		document.downloadSparqlForm.download.value = 'download';
		document.downloadSparqlForm.type.value = type;
		document.downloadSparqlForm.query.value = $("#userquary").val();
		document.downloadSparqlForm.submit();
	});
	
	// ì¤íí´ ë¤ì´ë¡ë
	$("#uquary").click(function(){
		document.downloadSparqlForm.action = "downSparql.jsp";
		document.downloadSparqlForm.query.value = $("#userquary").val();
		document.downloadSparqlForm.submit();
	});
	
	// ë²ì­
	$("#quarykor").click(function(){
		var qryValue = $("#userquary").val();
		if( qryValue.length == 0 ){			
			return;
		}
		$.ajax({
			type : 'GET',
			url : "sparqlTrans.jsp",
			data: ( {"qry" : qryValue}),
			success:function(msg){			
				$("#schxmlview").html("<textarea>"+msg+"</textarea>");				
			}
		});
	});
	
	 //$(document).ajaxStart($.blockUI).ajaxStop($.unblockUI);
});
