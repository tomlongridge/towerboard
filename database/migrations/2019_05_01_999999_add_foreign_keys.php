<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;

class AddForeignKeys extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::table('boards', function (Blueprint $table) {
            $table->foreign('created_by')->references('id')->on('users');
            $table->foreign('tower_id')->references('id')->on('towers');
        });

        Schema::table('notices', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards');
            $table->foreign('created_by')->references('id')->on('users');
        });

        Schema::table('board_subscriptions', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards')->onDelete('cascade');
            $table->foreign('user_id')->references('id')->on('users')->onDelete('cascade');
        });

        Schema::table('board_affiliates', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards')->onDelete('cascade');
            $table->foreign('affiliate_id')->references('id')->on('boards')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::table('board_affiliates', function (Blueprint $table) {
            $table->dropForeign(['board_id']);
            $table->dropForeign(['affiliate_id']);
        });

        Schema::table('board_subscriptions', function (Blueprint $table) {
            $table->dropForeign(['board_id']);
            $table->dropForeign(['user_id']);
        });

        Schema::table('notices', function (Blueprint $table) {
            $table->dropForeign(['board_id']);
        });

        Schema::table('boards', function (Blueprint $table) {
            $table->dropForeign(['tower_id']);
            $table->dropForeign(['created_by']);
        });
    }
}
