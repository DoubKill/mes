;(function () {

    var Main = {

        mixins: [BaseMixin],
        data: function () {
            return {
                tableDataUrl: PalletFeedbacksUrl,
                dialogRubberBarCodeInfoVisible: false,
                equip_no: null,
                product_no: null,
                st: null,
            }
        },
        methods: {

            search() {

                this.currentChange(this.currentPage)
            },
            beforeGetData: function () {

                this.getParams['equip_no'] = this.equip_no;
                this.getParams['product_no'] = this.product_no;
                this.getParams['st'] = this.st;
            },
            afterGetData: function () {

            },
            check_() {

                this.dialogRubberBarCodeInfoVisible = true
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')

})();