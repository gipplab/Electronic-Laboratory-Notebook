$(document).ready(function() {
   var collapsedGroups = {};
  
      var table = $('#ExpBase').DataTable({
        paging: false,
        //order: [[2, 'asc']],
        rowGroup: {
          // Uses the 'row group' plugin
          dataSrc: 7,
          startRender: function (rows, group) {
              var collapsed = !!collapsedGroups[group];
  
              rows.nodes().each(function (r) {
                  r.style.display = collapsed ? 'none' : '';
              });    
  
              // Add category name to the <tr>. NOTE: Hardcoded colspan
              return $('<tr/>')
                  .append('<td colspan="8">' + group + rows.nodes() + 'id' + ' (' + rows.count() + ') <a href="/Dash/GRP/SFG/' + group + '">Plot</a> </td>')
                  .attr('data-name', group)
                  .toggleClass('collapsed', collapsed);
          }
        }
      });
  
     $('#ExpBase tbody').on('click', 'tr.group-start', function () {
          var name = $(this).data('name');
          collapsedGroups[name] = !collapsedGroups[name];
          table.draw(false);
      });  
    
  });