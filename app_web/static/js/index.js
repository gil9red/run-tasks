$(function() {
    new DataTable('#table-tasks', {
        ajax: {
            url: '/api/tasks',
            dataSrc: '',
        },
        columns: [
            { data: 'id' },
            { data: 'name' },
            { data: 'description' },
            { data: 'cron' },
            { data: 'is_enabled' },
            { data: 'is_infinite' },
            { data: 'command' },
            { data: 'number_of_runs' },
        ]
    });
});
