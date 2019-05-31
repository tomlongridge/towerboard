<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;

class CreateTowers extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('towers', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->string('dove_id');
            $table->string('dedication');
            $table->string('area')->nullable();
            $table->string('town');
            $table->string('county');
            $table->string('country');
            $table->smallInteger('num_bells');
            $table->string('weight')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('towers');
    }
}
