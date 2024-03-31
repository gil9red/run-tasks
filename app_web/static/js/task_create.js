$(function() {
    $("form").submit(function() {
        let thisForm = this;
        let $this = $(this);

        let url = $this.attr("action");
        let method = $this.attr("method");
        if (method === undefined) {
            method = "get";
        }

        let data = convertFormToJSON(this);

        // Чекбоксы при убранном флаге не добавляются в значение
        // и при установленном флаге будет значение "on"
        // Поэтому, нужно вручную это сделать
        $this.find("input[type]").each((i, obj) => {
            let $obj = $(obj);
            data[$obj.attr("name")] = $obj.prop("checked");
        });

        $.ajax({
            url: url,
            method: method,  // HTTP метод, по умолчанию GET
            data: JSON.stringify(data),
            contentType: "application/json; charset=utf-8",
            dataType: "json",  // Тип данных загружаемых с сервера
            success: function(data) {
                on_ajax_success(
                    data,
                    null,
                    (css_selector_table, rs) => {
                        window.location.href = `/task/${rs.result[0].id}`;
                    }
                );

                // Очищение полей формы
                thisForm.reset();
            },
            error: data => on_ajax_error(data, 'при создании задачи'),
        });

        return false;
    });
});
