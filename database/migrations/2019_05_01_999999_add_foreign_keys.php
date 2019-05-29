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
            $table->foreign('owner_id')->references('id')->on('users');
            $table->foreign('tower_id')->references('id')->on('towers');
        });

        Schema::table('notices', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards');
        });


        Schema::table('guilds', function (Blueprint $table) {
            $table->foreign('affiliated_to')->references('id')->on('guilds');
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::table('notices', function (Blueprint $table) {
            $table->dropForeign(['board_id']);
        });
        Schema::table('boards', function (Blueprint $table) {
            $table->dropForeign(['tower_id']);
            $table->dropForeign(['owner_id']);
        });
    }
}
