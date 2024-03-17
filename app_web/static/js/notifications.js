$(function() {
    new DataTable('#table-notifications', {
        ajax: {
            url: `/api/notifications`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { data: 'id', title: 'id', },
            { data: 'task_run', title: 'task_run', },
            { data: 'name', title: 'name', },
            { data: 'text', title: 'text', },
            { data: 'kind', title: 'kind', },
            { data: 'append_date', title: 'append_date', },
            { data: 'sending_date', title: 'sending_date', },
        ],
        order: [
            // Сортировка по возрастанию id
            [0, "asc"],
        ],
    });
});
