function task_name_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }
    return `<a href="/task/${row.id}">${data}</a>`;
}

$(function() {
    new DataTable('#table-tasks', {
        ajax: {
            url: '/api/tasks',
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { data: 'id', title: 'id', },
            { data: 'name', title: 'Название', render: task_name_render, },
            { data: 'description', title: 'Описание', },
            { data: 'cron', title: 'Cron', },
            { data: 'is_enabled', title: 'is_enabled', },
            { data: 'is_infinite', title: 'is_infinite', },
            { data: 'command', title: 'command', },
            { data: 'number_of_runs', title: 'number_of_runs', },
        ]
    });
});
