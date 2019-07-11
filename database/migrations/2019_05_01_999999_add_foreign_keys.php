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

        Schema::table('board_subscriptions', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards')->onDelete('cascade');
            $table->foreign('user_id')->references('id')->on('users')->onDelete('cascade');
        });

        Schema::table('board_affiliates', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards')->onDelete('cascade');
            $table->foreign('affiliate_id')->references('id')->on('boards')->onDelete('cascade');
        });

        Schema::table('board_roles', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards')->onDelete('cascade');
            $table->foreign('user_id')->references('id')->on('users')->onDelete('cascade');
        });

        Schema::table('notices', function (Blueprint $table) {
            $table->foreign('board_id')->references('id')->on('boards');
            $table->foreign('created_by')->references('id')->on('users');
        });

        Schema::table('notice_messages', function (Blueprint $table) {
            $table->foreign('notice_id')->references('id')->on('notices')->onDelete('cascade');
            $table->foreign('created_by')->references('id')->on('users')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        if (Schema::hasTable('notice_messages')) {
            Schema::table('notice_messages', function (Blueprint $table) {
                $table->dropForeign(['notice_id']);
                $table->dropForeign(['created_by']);
            });
        }

        if (Schema::hasTable('notices')) {
            Schema::table('notices', function (Blueprint $table) {
                $table->dropForeign(['board_id']);
            });
        }

        if (Schema::hasTable('board_roles')) {
            Schema::table('board_roles', function (Blueprint $table) {
                $table->dropForeign(['board_id']);
                $table->dropForeign(['user_id']);
            });
        }

        if (Schema::hasTable('board_affiliates')) {
            Schema::table('board_affiliates', function (Blueprint $table) {
                $table->dropForeign(['board_id']);
                $table->dropForeign(['affiliate_id']);
            });
        }

        if (Schema::hasTable('board_subscriptions')) {
            Schema::table('board_subscriptions', function (Blueprint $table) {
                $table->dropForeign(['board_id']);
                $table->dropForeign(['user_id']);
            });
        }

        if (Schema::hasTable('boards')) {
            Schema::table('boards', function (Blueprint $table) {
                $table->dropForeign(['tower_id']);
                $table->dropForeign(['created_by']);
            });
        }
    }
}
