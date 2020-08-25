;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableDataUrl: RubberMaterialUrl,
                recipe_no: ''
            }
        },
        created: function () {

        },
        methods: {

            beforeGetData() {

                this.getParams["stage_product_batch_no"] = this.recipe_no;
            },
            recipeNoChanged: function () {

                this.getFirstPage();
            },

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();