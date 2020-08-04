;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: ProductInfosUrl,
                dialogAddRubberRecipe: false,
                originOptions: [],
                rubberRecipeForm: {
                    factory: null
                }
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {
                    class_name: '产地'
                }
            }).then(function (response) {

                app.originOptions = response.data.results;
            }).catch(function (error) {

            })
        },
        methods: {

            usedTypeFormatter: function (row, column) {

                return this.usedTypeChoice(row.used_type);
            },
            usedTypeChoice: function (usedType) {

                switch (usedType) {

                    case 1:
                        return "编辑";
                    case 2:
                        return "通过";
                    case 3:
                        return "应用";
                    case 4:
                        return "驳回";
                    case 5:
                        return "废弃";
                }
            },
            editButtonText: function (row) {

                switch (row.used_type) {

                    case 1:
                        return "应用";
                    case 3:
                        return "废弃";
                }
            },
            showAddRubberRecipeDialog: function () {

                this.dialogAddRubberRecipe = true;
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();